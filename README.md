# tennis-project
A repository for my data handling and infrastructure project

**Status:** work in progress. Raw ingestion and the raw BigQuery load are done. Cleaning, weather data, features and modelling are still to come.

## Instructions
Repo is private. Open notebooks in Google Colab (start with 00), upload requirements.txt when the first cell asks, then run the cells in order

## Data sources

| Source | What | Licence | How it is pinned |
|---|---|---|---|
| Jeff Sackmann's WTA match data, via the archival mirror [Aneeshers/tennis-sackmann-archive](https://github.com/Aneeshers/tennis-sackmann-archive) | Yearly match files `wta_matches_2010.csv` to `wta_matches_2026.csv` (43,924 rows) | CC BY-NC-SA 4.0 | Mirror commit `<PASTE FULL 40-CHARACTER COMMIT ID>`, with a sha256 checksum per file in `manifests/` |
| Open-Meteo historical weather API (planned) | Hourly weather per tournament venue | See Open-Meteo terms (attribution required; the free tier is for non-commercial use, to be verified) | Raw API responses are stored unchanged, with request parameters and a checksum manifest |

**Attribution:** tennis data collected and compiled by Jeff Sackmann / Tennis Abstract, used under CC BY-NC-SA 4.0. Sackmann's original repositories returned 404 on `<DATE CHECKED>`, so an unofficial mirror is used. It was checked by row counts and checksums, not by comparison with the original.

The data files are **not** included in this repository. The notebooks rebuild them from source.

## Storage design

| Stage | Location | Format | Why |
|---|---|---|---|
| Raw tennis | Cloud Storage bucket, `raw/tennis_sackmann_archive/<commit8>/wta/` | CSV, byte-for-byte as the source | Write-once, cheap, any format |
| Raw weather (planned) | Same bucket, `raw/open_meteo/...` | JSON, as returned by the API | Exact record of what the API said |
| Working tables | BigQuery: `tennis_raw`, `tennis_clean`, `tennis_features` | Partitioned tables | SQL joins and window functions, no servers to manage |
| Released datasets (planned) | Same bucket, `processed/features/release=<id>/` | Parquet | Typed, compressed, frozen snapshot for training |
| Models (planned) | Same bucket, `models/<release id>/` | joblib plus metadata JSON | Linked to the data they were trained on |

One bucket is used, with folders for each stage. The bucket and the datasets are in location **EU**.

A relational database (Cloud SQL) is not used. The workload is batch writes and bulk analytical reads, which BigQuery and Cloud Storage handle more cheaply, and Cloud SQL would bill continuously.

## Bucket protections

- Public access prevention enforced; uniform bucket-level access.
- Object versioning on, with a lifecycle rule that deletes old versions once 3 or more newer versions exist.
- Soft delete: `<CHECK AND FILL IN>`.
- Raw files are never overwritten: each source version goes to a new path.

## Data versioning

- **Raw tennis:** the source commit ID is in the storage path and in the manifest.
- **Raw weather (planned):** each fetch run writes to a new dated path, with a manifest of request parameters, fetch time and checksums.
- **Processed data (planned):** each release has an ID and a release manifest recording the source commit, weather run, code commit, row counts and checksum.
- **Code, manifests and `LOG.md`** are tracked in this repository. Bucket versioning is only a safety net against accidents, not the version history.

## Prerequisites to reproduce

1. A Google Cloud project with billing enabled. A budget alert is recommended.
2. Create these **Colab Secrets** and switch on Notebook access for each notebook:
   - `TENNIS_PROJECT_ID`: your Google Cloud project ID.
   - `TENNIS_BUCKET_NAME`: a globally unique bucket name containing no personal or project-identifying information.
3. The bucket and BigQuery datasets use location `EU`.
4. Run the notebooks in Google Colab. The repository is private, so upload `requirements.txt` to the session and run `pip install -r requirements.txt`. The file records the Python version used (see its first line).

## Run order

| Notebook | Purpose |
|---|---|
| `notebooks/00_gcp_setup.ipynb` | Sign-in, settings, enable services, create bucket and protections, create datasets, download the pinned files, upload to the bucket, write a manifest, check headers, load into `tennis_raw.wta_matches`, compare counts |
| `notebooks/01_explore_raw.ipynb` | SQL exploration of the raw table |
|
## Scope decisions

Modelling scope is tournament levels G, PM, P and I (38,998 matches). Level D (team events), O (Olympics), W (WTA 125 events), the ITF events and level F (season-ending events, round robin) are excluded. Reasons are in `LOG.md`.

## Known data issues

- Only the tournament start date exists, so match days must be estimated from the round.
- `minutes` is empty for all of 2010 to 2015; serve statistics are 10 to 22% empty for 2010 to 2015. Missingness follows time, so it is not imputed across that break.
- The 2015 WTA Finals is labelled level W instead of F (source error).
- `match_num` is not reliable for ordering matches.
- 2026 is a partial year (snapshot around June 2026), and 2020 is short (COVID).

## Repository layout

```
README.md   LOG.md   requirements.txt
notebooks/   manifests/
```
