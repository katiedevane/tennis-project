# Pipeline: raw -> clean (Apache Beam)

`tennis_pipeline.py` is the ETL version of notebooks 04 and 05. Notebook `14_pipeline.ipynb` runs it, tests it and reconciles it with the SQL (ELT) tables.

| Step (job graph name) | What it does |
|---|---|
| Match, OpenFiles, ReadRows | Find the raw files (gzip is opened automatically) and read each with its own header |
| RoundRobinRows, RoundRobinIds, DistinctIds | Events with a round-robin stage (a side input for Scope) |
| Scope | Out-of-scope rows (levels D, F, O, W, 35+H, 50+H; round-robin events) -> `excluded_rows`, with the reason |
| Validate | The data contract. Breaks it -> `bad_rows` (quarantine) with the reason. Odd but possible -> kept, flagged, counted |
| KeyByEdition, Format | Event format of each edition (CombineFn) |
| Date | Window of possible match days (event formats as a side input) |
| KeyDated, Summary, SummaryRow | One row per tournament edition (CombineFn) |
| Write_* | BigQuery (`--bq_dataset`, tables replaced on every run) or local JSON Lines (`--output`) |

**Quarantine reasons:** `missing:<columns>`, `bad_date`, `bad_tourney_id`, `bad_number:<column>`, `negative_value:<column>`, `bad_round:<value>`, `same_player_both_sides`, `bad_best_of`.

**Flags (row kept):** `flag_minutes` (over 300 minutes, or under 20 minutes for a finished match), `flag_serve_stats` (serve statistics that contradict each other).

**Counters:** `files_read`, `empty_files`, `rows_read`, `excluded_rows`, `bad_rows`, `good_rows`, `flag_minutes`, `flag_serve_stats`, `surface_carpet`, `hand_unknown`, `seed_code_to_entry`, `no_window`. They must reconcile: `rows_read = excluded_rows + bad_rows + good_rows`.

**Tests:** `python -m pytest -q test_tennis_pipeline.py` (expected: 8 passed).

**Local run (free):** `python tennis_pipeline.py --runner DirectRunner --input "data/raw/*.csv.gz" --output out/run`

**Dataflow (paid):** only from notebook 14, Part 7. The pipeline refuses to start on Dataflow without `--max_num_workers` 1 or 2 and a `--machine_type`.
