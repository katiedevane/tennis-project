"""WTA matches, raw -> clean, with Apache Beam (ETL).

Does in one pipeline what notebooks 04 (validate and type) and 05 (match-day windows) do in BigQuery SQL:

  Read     the compressed raw CSV, each file with its own header
  Scope    out-of-scope rows (other levels, round-robin events) go to `excluded`, with the reason
  Validate the data contract: rows that break it go to `bad` (the quarantine), with the reason;
           odd but possible values are kept, flagged and counted
  Format   the event format of each tournament edition (a CombineFn)
  Date     the window of possible match days of each match (event formats as a side input)
  Summary  one row per tournament edition (a CombineFn)
  Write    BigQuery (--bq_dataset) or local JSON Lines files (--output)

Counters reconcile: rows_read = excluded_rows + bad_rows + good_rows.

Run locally (free):   python tennis_pipeline.py --runner DirectRunner --input "data/raw/*.csv.gz" --output out/run
Run on Dataflow:      see notebook 14; the pipeline refuses to start on Dataflow without a worker cap of 1 or 2.
"""
import argparse
import csv
import io
import json
import logging
from datetime import datetime, timedelta

import apache_beam as beam
from apache_beam.io import fileio
from apache_beam.metrics import Metrics
from apache_beam.options.pipeline_options import (GoogleCloudOptions, PipelineOptions,
                                                  StandardOptions, WorkerOptions)

NS = "tennis"                                    # namespace of the counters
BAD = "bad"                                      # quarantine output: breaks the contract
EXCLUDED = "excluded"                            # out of scope: not wrong, just not modelled

LEVELS_IN_SCOPE = ("G", "PM", "P", "I")          # Grand Slam, Premier Mandatory, Premier, International
ROUNDS = ("R128", "R64", "R32", "R16", "QF", "SF", "F")
REQUIRED = ("tourney_id", "tourney_name", "tourney_date", "tourney_level", "surface", "round",
            "match_num", "winner_id", "loser_id", "score")

STATS = ("ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced")
INT_COLS = (("draw_size", "best_of", "match_num", "winner_id", "winner_seed", "winner_ht",
             "loser_id", "loser_seed", "loser_ht", "minutes")
            + tuple(f"{side}_{s}" for side in ("w", "l") for s in STATS)
            + ("winner_rank", "winner_rank_points", "loser_rank", "loser_rank_points"))
FLOAT_COLS = ("winner_age", "loser_age")
TEXT_COLS = ("winner_name", "winner_hand", "winner_ioc", "loser_name", "loser_hand", "loser_ioc", "score", "round")
SEED_COLS = ("winner_seed", "loser_seed")       # may hold entry codes (Q, WC, LL) instead of a number

# Days after tourney_date on which a round can be played: (earliest, latest). Same table as notebook 05.
WINDOWS = {
    "SLAM":      {"R128": (0, 1), "R64": (2, 3), "R32": (4, 5), "R16": (6, 7), "QF": (8, 9), "SF": (9, 11), "F": (11, 13)},
    "TWO_WEEK":  {"R128": (0, 4), "R64": (2, 6), "R32": (4, 8), "R16": (7, 10), "QF": (8, 11), "SF": (9, 12), "F": (11, 13)},
    "LONG_WEEK": {"R64": (0, 2), "R32": (1, 3), "R16": (2, 4), "QF": (3, 5), "SF": (4, 6), "F": (5, 7)},
    "ONE_WEEK":  {"R32": (0, 2), "R16": (1, 3), "QF": (2, 4), "SF": (3, 5), "F": (5, 6)},
}

MINUTES_MAX = 300          # longer than any plausible best-of-three match: flagged
MINUTES_MIN = 20           # shorter, and not a retirement, walkover or default: flagged


# ----------------------------------------------------------------------------- the contract, as plain functions

class RowError(Exception):
    """A row breaks the data contract; the message is the reason."""


def text(row, column):
    """Trimmed text, or None when empty (like NULLIF(TRIM(x), '') in notebook 04)."""
    value = (row.get(column) or "").strip()
    return value or None


def to_int(row, column):
    """Whole number, or None when empty. Anything else breaks the contract."""
    value = text(row, column)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        raise RowError("bad_number:" + column)


def to_float(row, column):
    value = text(row, column)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        raise RowError("bad_number:" + column)


def parse_date(value):
    """YYYYMMDD -> 'YYYY-MM-DD'."""
    try:
        return datetime.strptime((value or "").strip(), "%Y%m%d").date().isoformat()
    except ValueError:
        raise RowError("bad_date")


def scope_reason(row, round_robin_ids):
    """Why a row is out of scope, or None if it is in scope (same rule as notebook 04)."""
    level = row.get("tourney_level")
    if level not in LEVELS_IN_SCOPE:
        return "level:" + (level or "missing")
    if row.get("tourney_id") in round_robin_ids:
        return "round_robin_event"
    return None


def serve_stats_consistent(m, side):
    """False when one player's serve statistics contradict each other."""
    p = {s: m[f"{side}_{s}"] for s in STATS}
    if p["svpt"] is None:
        return True                                   # no statistics recorded: nothing to check
    second_serves = p["svpt"] - (p["1stIn"] or 0)
    checks = [
        p["svpt"] > 0,
        p["1stIn"] is None or p["1stIn"] <= p["svpt"],
        p["1stWon"] is None or p["1stIn"] is None or p["1stWon"] <= p["1stIn"],
        p["2ndWon"] is None or p["2ndWon"] <= second_serves,
        p["df"] is None or p["df"] <= second_serves,
        p["bpSaved"] is None or p["bpFaced"] is None or p["bpSaved"] <= p["bpFaced"],
    ]
    return all(checks)


def clean_match(row):
    """One raw in-scope row -> one typed match. Raises RowError if the row breaks the contract."""
    missing = [c for c in REQUIRED if text(row, c) is None]
    if missing:
        raise RowError("missing:" + ",".join(missing))

    m = {
        "match_id": f"{row['tourney_id']}-{row['match_num']}",
        "tourney_id": row["tourney_id"],
        "tourney_name": row["tourney_name"],
        "name_key": row["tourney_name"].strip().lower(),
        "tourney_date": parse_date(row["tourney_date"]),
        "tourney_level": row["tourney_level"],
        "surface": text(row, "surface").lower(),
    }
    try:
        m["season"] = int(row["tourney_id"][:4])
    except ValueError:
        raise RowError("bad_tourney_id")

    score = row.get("score") or ""
    m["is_walkover"] = "W/O" in score
    m["is_retirement"] = "RET" in score
    m["is_default"] = "DEF" in score

    for c in INT_COLS:
        if c not in SEED_COLS:
            m[c] = to_int(row, c)
    for c in FLOAT_COLS:
        m[c] = to_float(row, c)
    for c in TEXT_COLS:
        m[c] = text(row, c)

    # Seed: a number, or an entry code (Q, WC, LL...) that belongs in the entry column
    for side in ("winner", "loser"):
        seed = text(row, f"{side}_seed")
        entry = text(row, f"{side}_entry")
        try:
            m[f"{side}_seed"] = int(seed) if seed is not None else None
            code = None
        except ValueError:
            m[f"{side}_seed"] = None
            code = seed.upper()
        m[f"{side}_entry"] = entry.upper() if entry is not None else code
        m[f"_{side}_seed_code"] = code is not None and entry is None

    # Impossible values: quarantine
    if m["round"] not in ROUNDS:
        raise RowError("bad_round:" + str(m["round"]))
    if m["winner_id"] == m["loser_id"]:
        raise RowError("same_player_both_sides")
    for c in INT_COLS:
        if m[c] is not None and m[c] < 0:
            raise RowError("negative_value:" + c)
    if m["best_of"] not in (None, 3, 5):
        raise RowError("bad_best_of")

    # Odd but possible: keep, flag, count
    finished = not (m["is_walkover"] or m["is_retirement"] or m["is_default"])
    m["flag_minutes"] = m["minutes"] is not None and (
        m["minutes"] > MINUTES_MAX or (finished and m["minutes"] < MINUTES_MIN))
    m["flag_serve_stats"] = not (serve_stats_consistent(m, "w") and serve_stats_consistent(m, "l"))
    return m


def event_format(level, rounds):
    """Event format of a tournament edition, from its level and the rounds played (notebook 05)."""
    if level == "G":
        return "SLAM"
    if "R128" in rounds:
        return "TWO_WEEK"
    if "R64" in rounds:
        return "LONG_WEEK"
    return "ONE_WEEK"


def match_window(match, fmt):
    """Add the window of possible match days. Returns False when the round has no window in that format."""
    lo_hi = WINDOWS.get(fmt, {}).get(match["round"])
    match["event_format"] = fmt
    if lo_hi is None:
        match.update(day_min=None, day_max=None, match_date_min=None, match_date_max=None)
        return False
    start = datetime.strptime(match["tourney_date"], "%Y-%m-%d").date()
    match["day_min"], match["day_max"] = lo_hi
    match["match_date_min"] = (start + timedelta(days=lo_hi[0])).isoformat()
    match["match_date_max"] = (start + timedelta(days=lo_hi[1])).isoformat()
    return True


# ----------------------------------------------------------------------------- Beam steps

class ReadCsvFile(beam.DoFn):
    """One element in = one file (gzip is opened automatically). Each file is read with its own header."""

    def __init__(self):
        self.files = Metrics.counter(NS, "files_read")
        self.empty = Metrics.counter(NS, "empty_files")
        self.rows = Metrics.counter(NS, "rows_read")

    def process(self, readable_file):
        name = readable_file.metadata.path.rsplit("/", 1)[-1]
        self.files.inc()
        count = 0
        # Beam's file object for .gz files is not a full Python file (TextIOWrapper cannot wrap it),
        # so the decompressed bytes are read first. Fine at this size (about 9 MB uncompressed).
        with readable_file.open() as raw:
            content = io.TextIOWrapper(io.BytesIO(raw.read()), encoding="utf-8-sig", newline="")
            for row in csv.DictReader(content):
                count += 1
                row["_source"] = name
                row["_line"] = count + 1                 # line in the file (the header is line 1)
                yield row
        self.rows.inc(count)
        if count == 0:
            self.empty.inc()


class Scope(beam.DoFn):
    """In-scope rows continue; the rest go to EXCLUDED with the reason. Not an error: a modelling choice."""

    def __init__(self):
        self.excluded = Metrics.counter(NS, "excluded_rows")

    def process(self, row, round_robin_ids):
        reason = scope_reason(row, set(round_robin_ids))
        if reason is None:
            yield row
            return
        self.excluded.inc()
        yield beam.pvalue.TaggedOutput(EXCLUDED, {
            "reason": reason, "source": row.get("_source"), "line": row.get("_line"),
            "tourney_id": row.get("tourney_id"), "tourney_name": row.get("tourney_name"),
            "tourney_level": row.get("tourney_level")})


class ValidateMatch(beam.DoFn):
    """The data contract as code. Good rows go to the main output, bad rows to BAD with the reason."""

    def __init__(self):
        self.good = Metrics.counter(NS, "good_rows")
        self.bad = Metrics.counter(NS, "bad_rows")
        self.minutes = Metrics.counter(NS, "flag_minutes")
        self.serve = Metrics.counter(NS, "flag_serve_stats")
        self.carpet = Metrics.counter(NS, "surface_carpet")
        self.hand = Metrics.counter(NS, "hand_unknown")
        self.seed_code = Metrics.counter(NS, "seed_code_to_entry")

    def process(self, row):
        try:
            m = clean_match(row)
        except RowError as err:
            self.bad.inc()
            raw = {k: v for k, v in row.items() if not k.startswith("_")}
            yield beam.pvalue.TaggedOutput(BAD, {
                "reason": str(err), "source": row.get("_source"), "line": row.get("_line"),
                "raw": json.dumps(raw)[:2000]})
            return
        self.good.inc()
        self.minutes.inc(int(m["flag_minutes"]))
        self.serve.inc(int(m["flag_serve_stats"]))
        self.carpet.inc(int(m["surface"] == "carpet"))
        self.hand.inc(int(m["winner_hand"] == "U") + int(m["loser_hand"] == "U"))
        self.seed_code.inc(int(m.pop("_winner_seed_code")) + int(m.pop("_loser_seed_code")))
        m["source_file"] = row.get("_source")
        yield m


class EventFormat(beam.CombineFn):
    """Per tournament edition: its level and the set of rounds played -> the event format."""

    def create_accumulator(self):
        return (None, frozenset())

    def add_input(self, acc, level_round):
        level, rounds = acc
        new_level, new_round = level_round
        return (level or new_level, rounds | {new_round})

    def merge_accumulators(self, accs):
        level, rounds = None, frozenset()
        for a_level, a_rounds in accs:
            level, rounds = level or a_level, rounds | a_rounds
        return (level, rounds)

    def extract_output(self, acc):
        return event_format(*acc)


class DateMatch(beam.DoFn):
    """Add the event format (a side input) and the window of possible match days."""

    def __init__(self):
        self.no_window = Metrics.counter(NS, "no_window")

    def process(self, match, formats):
        if not match_window(match, formats.get(match["tourney_id"])):
            self.no_window.inc()
        yield match


class EditionStats(beam.CombineFn):
    """Per tournament edition: matches, results that were not a full match, flags, dates."""

    FIELDS = ("matches", "walkovers", "retirements", "defaults", "flagged_minutes", "flagged_serve_stats")

    def create_accumulator(self):
        return {"counts": dict.fromkeys(self.FIELDS, 0), "first": None, "last": None, "info": None}

    def add_input(self, acc, m):
        c = acc["counts"]
        c["matches"] += 1
        c["walkovers"] += int(m["is_walkover"])
        c["retirements"] += int(m["is_retirement"])
        c["defaults"] += int(m["is_default"])
        c["flagged_minutes"] += int(m["flag_minutes"])
        c["flagged_serve_stats"] += int(m["flag_serve_stats"])
        acc["first"] = min(filter(None, [acc["first"], m["tourney_date"]]), default=None)
        acc["last"] = max(filter(None, [acc["last"], m["match_date_max"]]), default=None)
        acc["info"] = acc["info"] or {k: m[k] for k in ("tourney_name", "name_key", "season", "tourney_level",
                                                         "surface", "event_format", "draw_size")}
        return acc

    def merge_accumulators(self, accs):
        out = self.create_accumulator()
        for a in accs:
            for k in self.FIELDS:
                out["counts"][k] += a["counts"][k]
            out["first"] = min(filter(None, [out["first"], a["first"]]), default=None)
            out["last"] = max(filter(None, [out["last"], a["last"]]), default=None)
            out["info"] = out["info"] or a["info"]
        return out

    def extract_output(self, acc):
        return {**(acc["info"] or {}), **acc["counts"], "start_date": acc["first"], "last_match_day": acc["last"]}


def build(p, args):
    """Wire the pipeline. Returns the four results: matches, bad, excluded, editions."""
    rows = (p
            | "Match" >> fileio.MatchFiles(args.input)
            | "OpenFiles" >> fileio.ReadMatches()
            | "ReadRows" >> beam.ParDo(ReadCsvFile()))

    round_robin = (rows
                   | "RoundRobinRows" >> beam.Filter(lambda r: r.get("round") == "RR")
                   | "RoundRobinIds" >> beam.Map(lambda r: r.get("tourney_id"))
                   | "DistinctIds" >> beam.Distinct())

    scoped = rows | "Scope" >> beam.ParDo(
        Scope(), round_robin_ids=beam.pvalue.AsList(round_robin)).with_outputs(EXCLUDED, main="in_scope")

    checked = scoped.in_scope | "Validate" >> beam.ParDo(ValidateMatch()).with_outputs(BAD, main="good")

    formats = (checked.good
               | "KeyByEdition" >> beam.Map(lambda m: (m["tourney_id"], (m["tourney_level"], m["round"])))
               | "Format" >> beam.CombinePerKey(EventFormat()))

    matches = checked.good | "Date" >> beam.ParDo(DateMatch(), formats=beam.pvalue.AsDict(formats))

    editions = (matches
                | "KeyDated" >> beam.Map(lambda m: (m["tourney_id"], m))
                | "Summary" >> beam.CombinePerKey(EditionStats())
                | "SummaryRow" >> beam.MapTuple(lambda tid, stats: {"tourney_id": tid, **stats}))

    return matches, checked[BAD], scoped[EXCLUDED], editions


# ----------------------------------------------------------------------------- output

def _schema(pairs):
    return ",".join(f"{name}:{kind}" for name, kind in pairs)


MATCH_SCHEMA = _schema(
    [("match_id", "STRING"), ("tourney_id", "STRING"), ("tourney_name", "STRING"), ("name_key", "STRING"),
     ("tourney_date", "DATE"), ("season", "INTEGER"), ("tourney_level", "STRING"), ("surface", "STRING"),
     ("is_walkover", "BOOLEAN"), ("is_retirement", "BOOLEAN"), ("is_default", "BOOLEAN")]
    + [(c, "INTEGER") for c in INT_COLS] + [(c, "FLOAT") for c in FLOAT_COLS] + [(c, "STRING") for c in TEXT_COLS]
    + [("winner_entry", "STRING"), ("loser_entry", "STRING"), ("flag_minutes", "BOOLEAN"),
       ("flag_serve_stats", "BOOLEAN"), ("source_file", "STRING"), ("event_format", "STRING"),
       ("day_min", "INTEGER"), ("day_max", "INTEGER"), ("match_date_min", "DATE"), ("match_date_max", "DATE")])
BAD_SCHEMA = "reason:STRING,source:STRING,line:INTEGER,raw:STRING"
EXCLUDED_SCHEMA = "reason:STRING,source:STRING,line:INTEGER,tourney_id:STRING,tourney_name:STRING,tourney_level:STRING"
EDITION_SCHEMA = _schema(
    [("tourney_id", "STRING"), ("tourney_name", "STRING"), ("name_key", "STRING"), ("season", "INTEGER"),
     ("tourney_level", "STRING"), ("surface", "STRING"), ("event_format", "STRING"), ("draw_size", "INTEGER")]
    + [(f, "INTEGER") for f in EditionStats.FIELDS] + [("start_date", "DATE"), ("last_match_day", "DATE")])

OUTPUTS = (("matches_dated", MATCH_SCHEMA), ("bad_rows", BAD_SCHEMA),
           ("excluded_rows", EXCLUDED_SCHEMA), ("edition_summary", EDITION_SCHEMA))


def write_results(results, args, project):
    """BigQuery when --bq_dataset is given (tables replaced on every run), local JSON Lines files otherwise."""
    for pcoll, (table, schema) in zip(results, OUTPUTS):
        if args.bq_dataset:
            pcoll | f"Write_{table}" >> beam.io.WriteToBigQuery(
                f"{project}:{args.bq_dataset}.{table}", schema=schema,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
                write_disposition=beam.io.BigQueryDisposition.WRITE_TRUNCATE,   # re-running never duplicates
                method=beam.io.WriteToBigQuery.Method.FILE_LOADS)
        else:
            (pcoll
             | f"Json_{table}" >> beam.Map(json.dumps)
             | f"Write_{table}" >> beam.io.WriteToText(f"{args.output}_{table}", file_name_suffix=".jsonl"))


def print_counters(result):
    counters = {c.key.metric.name: c.result for c in result.metrics().query()["counters"]
                if c.key.metric.namespace == NS}
    for name in sorted(counters):
        print(f"  {name:20s} {counters[name]:>8,}")
    parts = sum(counters.get(k, 0) for k in ("excluded_rows", "bad_rows", "good_rows"))
    ok = parts == counters.get("rows_read", 0)
    print(f"  check: rows_read {counters.get('rows_read', 0):,} = excluded + bad + good {parts:,} ->",
          "OK" if ok else "MISMATCH")
    return counters


# ----------------------------------------------------------------------------- run

def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--input", required=True, help="raw file pattern, local or gs://")
    parser.add_argument("--output", default="out/run", help="local output prefix (when --bq_dataset is not given)")
    parser.add_argument("--bq_dataset", default=None, help="write to this BigQuery dataset instead of files")
    return parser.parse_known_args(argv)


def check_cost_guardrails(options):
    """Refuse to start a Dataflow job without a worker cap: autoscaling can otherwise use many workers."""
    if options.view_as(StandardOptions).runner not in ("DataflowRunner", "dataflow"):
        return
    workers = options.view_as(WorkerOptions).max_num_workers
    if workers not in (1, 2):
        raise SystemExit("Refusing to run on Dataflow without --max_num_workers 1 or 2 (cost guardrail).")
    if not options.view_as(WorkerOptions).machine_type:
        raise SystemExit("Refusing to run on Dataflow without --machine_type (use e2-standard-2).")


def run(argv=None):
    args, beam_args = parse_args(argv)
    options = PipelineOptions(beam_args, save_main_session=True)
    check_cost_guardrails(options)
    project = options.view_as(GoogleCloudOptions).project
    if args.bq_dataset and not project:
        raise SystemExit("--bq_dataset needs --project")
    local = options.view_as(StandardOptions).runner in (None, "DirectRunner")
    if local:
        logging.getLogger().setLevel(logging.WARNING)

    pipeline = beam.Pipeline(options=options)
    write_results(build(pipeline, args), args, project)
    result = pipeline.run()
    result.wait_until_finish()
    print("Counters:")
    print_counters(result)


if __name__ == "__main__":
    run()
