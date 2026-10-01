# Project log

## Setup

- 2026-09-28 Created the Google Cloud project on the website and linked billing (credit applied).
- 2026-09-28 Workflow decision: work in Google Colab. Non-secret settings are read from Colab Secrets (`TENNIS_PROJECT_ID`, `TENNIS_BUCKET_NAME`); prefixed names avoid clashes with other projects. No key files are used.
- 2026-09-29 Bucket name follows Google's naming guidance. One bucket is used, with folders for each stage.
- 2026-09-29 Enabled the Storage and BigQuery APIs from notebook 00. Secret Manager deferred until a real secret is needed (the Open-Meteo free tier needs no key).
- 2026-09-29 Created the bucket from code (location EU, uniform access, public access prevention enforced). Versioning on; lifecycle rule deletes old versions once 3+ newer versions exist. The first attempt with a dictionary-style rule did not save; the library helper methods worked and the settings were read back to confirm.
-  2026-09-29 Created BigQuery datasets `tennis_raw`, `tennis_clean`, `tennis_features` (location EU). Layers: raw (unedited), clean (typed and tidied), features (model-ready).
-  2026-09-29 `requirements.txt` generated from the Colab runtime (Python `<version>`). Rule: update it whenever a new library is used.

## Data source decisions

- 2026-09-28 Sackmann's original repositories returned 404. Chose the archival mirror Aneeshers/tennis-sackmann-archive (CC BY-NC-SA 4.0), pinned to commit `<FULL 40-CHARACTER ID>`. Mirror is unofficial, so it was checked by row counts and checksums.
- Not used: tennis-data.co.uk (terms restrict automated and AI use) and TennisMyLife (licence wording unclear across its site and README).
- Repository is private. `requirements.txt` is uploaded to Colab each session instead of using an access token.

## Ingestion

- 2026-09-29 Downloaded `wta_matches_2010` to `wta_matches_2026` (17 files, 43,924 rows) from the pinned commit into `raw/tennis_sackmann_archive/83733587/wta/`. Manifest `manifests/wta_matches_83733587_20260929T173941Z.json` records the URL, row count and sha256 of each file. Raw files are never overwritten.
- 2026-09-29 Loaded all files into `tennis_raw.wta_matches` with every column as STRING (nothing is guessed at load). All files had an identical header row. Table count of 43,924 equals the download total, with yearly counts matching.

## Exploration findings

- No duplicates: 43,924 rows = 43,924 unique (tourney_id, match_num).
- Only `tourney_date` exists (tournament start, usually a Monday). Match days must be estimated from round and draw size.
- `minutes` is empty for all of 2010 to 2015 and filled from 2016; serve stats are 10 to 13% empty 2010 to 2014 and 22% in 2015, then about 0 to 2% from 2016. 2026 is about 13% empty (partial year). Missingness follows time, so do not impute across the break.
- Seed and entry columns: empty means "none". Height is empty for 10 to 15% and can be filled from the player's other matches. Rank is 1.4 to 2.8% empty.
- `surface` has inconsistent case (Clay / clay) and is missing for 115 team-event rows.
- Level codes: G = Slams, PM = Premier Mandatory, P = Premier, I = International, F = season-ending events, D = team events. From tournament names: W = WTA 125 events, O = Olympics, 35+H and 50+H = lower-tier ITF events.
- The 2015 WTA Finals (15 matches, 2015-10-25) is labelled W instead of F: a source error.
- `tourney_id` suffixes are not a reliable venue key (for example, Tokyo and Osaka share one), so the venue table is keyed on the cleaned tournament name.
- Anything about the match itself (score, minutes, w_* and l_* statistics) can only enter the model as history, never as a feature of the same match.

## Scope decisions

- Modelling scope: levels G, PM, P, I = 38,998 matches (about 24,400 from 2016).
- Excluded: D (team format, 62% missing serve stats), O (different format), W (few one-off editions), ITF levels (few, one-off), F (344 matches: round robin cannot be mapped to match days, mostly indoor, host city changes yearly). F can be reinstated later with the 2015 label corrected in staging.
- Open decision: model on 2010 onward (minutes excluded, earlier years used for rating warm-up) or 2016 onward only (all stats available).

## Venue table

- 2026-09-30 Created 02_venues.ipynb. Venue list rebuilt from tennis_raw (levels G, PM, P, I): 144 names, 122 places after hand mappings in code; 1 (united cup) excluded. Geocoded via Open-Meteo Geocoding API (no key needed): raw responses stored write-once under raw/open_meteo/geocoding/ with request and fetch time; manifest manifests/open_meteo_geocoding_<stamp>.json. 
- 2026-09-30 Reviewed geocoding results for 122 places. Corrections (in code, notebook 02): Bol (HR), Granby (CA), Indian Wells (2nd result, since the top is Indio), Marrakech searched as 'Marrakesh', Quebec City searched as 'Quebec' (CA), Stanford uses Palo Alto as a proxy, Mallorca uses Calvia. Coordinates are city-level (Miami, US Open, Wimbledon approximated), which is acceptable for a coarse weather grid. Saved tennis_clean.venue_locations (122 rows) and reference/venues/v1/venue_locations.csv. Manifest saved: manifests/open_meteo_geocoding_20260930T213952Z.json
- 2026-09-30 Built tournament_editions (one row per edition, levels G/PM/P/I): <n> rows, each with coordinates and a fetch window (start date to +7 days; +14 for G and PM). United Cup has no location and is dropped. Saved tennis_clean.tournament_editions and reference/editions/v1/tournament_editions.csv (write-once).
- 2026-09-30 Design decision: fetch weather with the ERA5 model pinned for every edition, because Open-Meteo's default model changes over time (newer 9 km models from 2017), which would create a false break in 2017. Indoor/outdoor flag is not needed to fetch weather; it will be applied at feature-building time.
- 2026-10-01 Fetched ERA5 hourly weather for 873 tournament editions (start date to +7 days, +14 for G/PM) from the Open-Meteo archive API, model pinned to era5 (<result of the Cell 4 test>). Variables: temperature_2m, relative_humidity_2m, dew_point_2m, surface_pressure, precipitation, wind_speed_10m, wind_gusts_10m, wind_direction_10m, cloud_cover; timezone=auto (local hours). Raw responses stored write-once at raw/open_meteo/archive/model=era5/<tourney_id>.json with request and fetch time; manifest manifests/open_meteo_archive_era5_<stamp>.json. Validation: <files, null values, hour mismatches>.
