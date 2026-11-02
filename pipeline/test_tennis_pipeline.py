"""Unit tests for tennis_pipeline.py. Run: python -m pytest -q test_tennis_pipeline.py

Small known inputs, checked with Beam's TestPipeline (local, free). Expected: 9 passed.
"""
import gzip

import apache_beam as beam
from apache_beam.io import fileio
from apache_beam.testing.test_pipeline import TestPipeline as BeamTestPipeline   # alias: pytest would try to collect a class named Test*
from apache_beam.testing.util import assert_that, equal_to

import tennis_pipeline as tp

# One valid in-scope row, with every raw column as text (as csv.DictReader gives it)
GOOD = {
    "tourney_id": "2019-0560", "tourney_name": "Us Open", "surface": "Hard", "draw_size": "128",
    "tourney_level": "G", "tourney_date": "20190826", "match_num": "100",
    "winner_id": "201", "winner_seed": "3", "winner_entry": "", "winner_name": "Player One",
    "winner_hand": "R", "winner_ht": "175", "winner_ioc": "USA", "winner_age": "24.5",
    "loser_id": "202", "loser_seed": "", "loser_entry": "", "loser_name": "Player Two",
    "loser_hand": "L", "loser_ht": "", "loser_ioc": "FRA", "loser_age": "21.2",
    "score": "6-3 6-4", "best_of": "3", "round": "R128", "minutes": "85",
    "w_ace": "5", "w_df": "2", "w_svpt": "60", "w_1stIn": "40", "w_1stWon": "30", "w_2ndWon": "10",
    "w_SvGms": "9", "w_bpSaved": "2", "w_bpFaced": "3",
    "l_ace": "1", "l_df": "4", "l_svpt": "65", "l_1stIn": "38", "l_1stWon": "22", "l_2ndWon": "12",
    "l_SvGms": "10", "l_bpSaved": "4", "l_bpFaced": "8",
    "winner_rank": "3", "winner_rank_points": "5000", "loser_rank": "80", "loser_rank_points": "700",
    "_source": "test.csv", "_line": 2,
}


def validate(rows):
    return (rows | beam.ParDo(tp.ValidateMatch()).with_outputs(tp.BAD, main="good"))


def test_validate_sends_good_and_bad_rows_to_the_right_place():
    rows = [GOOD,
            dict(GOOD, winner_id=""),
            dict(GOOD, tourney_date="2019-08-26"),
            dict(GOOD, w_ace="many"),
            dict(GOOD, l_df="-1"),
            dict(GOOD, loser_id="201"),
            dict(GOOD, round="Q1")]
    reasons = ["missing:winner_id", "bad_date", "bad_number:w_ace", "negative_value:l_df",
               "same_player_both_sides", "bad_round:Q1"]
    with BeamTestPipeline() as p:
        out = validate(p | beam.Create(rows))
        assert_that(out.good | beam.combiners.Count.Globally(), equal_to([1]), label="one good row")
        assert_that(out[tp.BAD] | beam.Map(lambda r: r["reason"]), equal_to(reasons), label="six reasons")


def test_scope_excludes_other_levels_and_round_robin_events():
    rows = [GOOD,
            dict(GOOD, tourney_level="D"),
            dict(GOOD, tourney_id="2020-RR01")]
    with BeamTestPipeline() as p:
        rr = p | "RR" >> beam.Create(["2020-RR01"])
        out = (p | beam.Create(rows)
               | beam.ParDo(tp.Scope(), round_robin_ids=beam.pvalue.AsList(rr)).with_outputs(tp.EXCLUDED, main="in_scope"))
        assert_that(out.in_scope | beam.combiners.Count.Globally(), equal_to([1]), label="one in scope")
        assert_that(out[tp.EXCLUDED] | beam.Map(lambda r: r["reason"]),
                    equal_to(["level:D", "round_robin_event"]), label="two reasons")


def test_typing_matches_notebook_04():
    m = tp.clean_match(GOOD)
    assert m["match_id"] == "2019-0560-100"
    assert m["tourney_date"] == "2019-08-26" and m["season"] == 2019
    assert m["surface"] == "hard" and m["name_key"] == "us open"
    assert m["winner_seed"] == 3 and m["loser_seed"] is None and m["loser_ht"] is None
    assert m["winner_age"] == 24.5 and m["w_svpt"] == 60
    assert not m["is_walkover"] and not m["flag_minutes"] and not m["flag_serve_stats"]


def test_seed_codes_move_to_the_entry_column():
    m = tp.clean_match(dict(GOOD, winner_seed="q", winner_entry="", loser_seed="2", loser_entry="wc"))
    assert m["winner_seed"] is None and m["winner_entry"] == "Q"
    assert m["loser_seed"] == 2 and m["loser_entry"] == "WC"


def test_odd_values_are_kept_and_flagged_not_dropped():
    long_match = tp.clean_match(dict(GOOD, minutes="2475"))
    short_finished = tp.clean_match(dict(GOOD, minutes="0"))
    short_retired = tp.clean_match(dict(GOOD, minutes="10", score="6-1 RET"))
    bad_serve = tp.clean_match(dict(GOOD, w_df="25"))             # more double faults than second serves (20)
    assert long_match["flag_minutes"] and short_finished["flag_minutes"]
    assert not short_retired["flag_minutes"] and short_retired["is_retirement"]
    assert bad_serve["flag_serve_stats"]


def test_event_format_combines_correctly():
    readings = [("slam", ("G", "R128")), ("slam", ("G", "F")),
                ("two", ("P", "R32")), ("two", ("P", "R128")),
                ("long", ("I", "R64")), ("one", ("I", "R32")), ("one", ("I", "F"))]
    with BeamTestPipeline() as p:
        out = p | beam.Create(readings) | beam.CombinePerKey(tp.EventFormat())
        assert_that(out, equal_to([("slam", "SLAM"), ("two", "TWO_WEEK"), ("long", "LONG_WEEK"), ("one", "ONE_WEEK")]))


def test_match_window_follows_notebook_05():
    m = tp.clean_match(dict(GOOD, round="F"))
    assert tp.match_window(m, "SLAM")
    assert (m["day_min"], m["day_max"]) == (11, 13)
    assert (m["match_date_min"], m["match_date_max"]) == ("2019-09-06", "2019-09-08")
    unknown = tp.clean_match(GOOD)
    assert not tp.match_window(unknown, "ONE_WEEK")               # no R128 in a one-week event
    assert unknown["match_date_min"] is None


def test_edition_summary_counts_matches():
    a = tp.clean_match(GOOD)
    b = tp.clean_match(dict(GOOD, match_num="101", score="W/O", round="R64"))
    for m in (a, b):
        tp.match_window(m, "SLAM")
    with BeamTestPipeline() as p:
        out = (p | beam.Create([("2019-0560", a), ("2019-0560", b)])
               | beam.CombinePerKey(tp.EditionStats())
               | beam.MapTuple(lambda tid, s: (tid, s["matches"], s["walkovers"], s["start_date"], s["last_match_day"])))
        assert_that(out, equal_to([("2019-0560", 2, 1, "2019-08-26", "2019-08-29")]))


def test_reads_a_gzip_file_with_its_header(tmp_path):
    """The real input is a .gz file opened by Beam's own file object (not a plain Python file)."""
    columns = [c for c in GOOD if not c.startswith("_")]
    lines = [",".join(columns)] + [",".join(str(dict(GOOD, match_num=str(n))[c]) for c in columns) for n in (1, 2, 3)]
    (tmp_path / "part.csv.gz").write_bytes(gzip.compress(("\n".join(lines) + "\n").encode()))
    with BeamTestPipeline() as p:
        rows = (p | fileio.MatchFiles(str(tmp_path / "*.csv.gz")) | fileio.ReadMatches()
                  | beam.ParDo(tp.ReadCsvFile()))
        assert_that(rows | beam.Map(lambda r: (r["match_num"], r["_source"], r["_line"])),
                    equal_to([("1", "part.csv.gz", 2), ("2", "part.csv.gz", 3), ("3", "part.csv.gz", 4)]))
