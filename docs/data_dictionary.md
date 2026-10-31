# Data dictionary (draft)

Draft written from the notebook code (types as defined in notebooks 02-10). Run `11_data_dictionary` to regenerate it from the live BigQuery schemas, with % missing per column.

`known before match` says what a model may use directly. `no (post-match)` columns may only be used as history, i.e. in features built from *earlier* matches.

## Raw files (bucket)

| file | format | contents |
|---|---|---|
| `raw/tennis_sackmann_archive/83733587/wta/wta_matches_2010_2026.csv.gz` | gzip CSV, header once | All seasons 2010-2026 from the pinned commit; columns as `tennis_raw.wta_matches` |
| `raw/open_meteo/geocoding/packed/geocoding_<sha>.jsonl.gz` | gzip JSON Lines | One line per place query: `key`, `request` (url, params), `fetched_at_utc`, `response` (API output as returned) |
| `raw/open_meteo/archive_v2/model=era5/packed/weather_era5_<sha>.jsonl.gz` | gzip JSON Lines | One line per tournament edition: `tourney_id`, `request`, `fetched_at_utc`, `response` |

Hourly weather variables (ERA5, local time of the venue): `temperature_2m` (°C), `relative_humidity_2m` (%), `dew_point_2m` (°C), `surface_pressure` (hPa), `precipitation` (mm), `wind_speed_10m` (km/h), `wind_gusts_10m` (km/h), `wind_direction_10m` (°), `cloud_cover` (%). Units are also stored in each response's `hourly_units`.

## tennis_raw.wta_matches

Raw WTA matches, every column STRING (external table over the compressed CSV in the bucket). Typed in 04_clean_matches.

| column | type | known before match | description |
|---|---|---|---|
| `tourney_id` | STRING | yes | Tournament edition ID: season year + tournament code |
| `tourney_name` | STRING | yes | Tournament name as in the source |
| `surface` | STRING | yes | Court surface: hard, clay, grass (lower-cased from 04 on) (text here; typed in 04) |
| `draw_size` | STRING | yes | Number of players in the main draw (text here; typed in 04) |
| `tourney_level` | STRING | yes | Level: G = Grand Slam, PM = Premier Mandatory, P = Premier, I = International. Raw also has D, O, W, 35+H, 50+H (excluded in 04) (text here; typed in 04) |
| `tourney_date` | STRING | yes | Tournament start date (raw: text YYYYMMDD). Not the match date (text here; typed in 04) |
| `match_num` | STRING | id | Match number within the tournament (text here; typed in 04) |
| `winner_id` | STRING | yes, but the winner/loser side reveals the result | Winner: player ID (stable across seasons) (text here; typed in 04) |
| `winner_seed` | STRING | yes, but the winner/loser side reveals the result | Winner: seed number (NULL = unseeded; raw may hold entry codes) (text here; typed in 04) |
| `winner_entry` | STRING | yes, but the winner/loser side reveals the result | Winner: entry: Q qualifier, WC wildcard, LL lucky loser, PR protected ranking, SE special exempt, ALT alternate; NULL = direct entry (text here; typed in 04) |
| `winner_name` | STRING | yes, but the winner/loser side reveals the result | Winner: player name (text here; typed in 04) |
| `winner_hand` | STRING | yes, but the winner/loser side reveals the result | Winner: playing hand: R, L, U = unknown (text here; typed in 04) |
| `winner_ht` | STRING | yes, but the winner/loser side reveals the result | Winner: height, cm (text here; typed in 04) |
| `winner_ioc` | STRING | yes, but the winner/loser side reveals the result | Winner: country, 3-letter IOC code (text here; typed in 04) |
| `winner_age` | STRING | yes, but the winner/loser side reveals the result | Winner: age in years at tourney_date (text here; typed in 04) |
| `loser_id` | STRING | yes, but the winner/loser side reveals the result | Loser: player ID (stable across seasons) (text here; typed in 04) |
| `loser_seed` | STRING | yes, but the winner/loser side reveals the result | Loser: seed number (NULL = unseeded; raw may hold entry codes) (text here; typed in 04) |
| `loser_entry` | STRING | yes, but the winner/loser side reveals the result | Loser: entry: Q qualifier, WC wildcard, LL lucky loser, PR protected ranking, SE special exempt, ALT alternate; NULL = direct entry (text here; typed in 04) |
| `loser_name` | STRING | yes, but the winner/loser side reveals the result | Loser: player name (text here; typed in 04) |
| `loser_hand` | STRING | yes, but the winner/loser side reveals the result | Loser: playing hand: R, L, U = unknown (text here; typed in 04) |
| `loser_ht` | STRING | yes, but the winner/loser side reveals the result | Loser: height, cm (text here; typed in 04) |
| `loser_ioc` | STRING | yes, but the winner/loser side reveals the result | Loser: country, 3-letter IOC code (text here; typed in 04) |
| `loser_age` | STRING | yes, but the winner/loser side reveals the result | Loser: age in years at tourney_date (text here; typed in 04) |
| `score` | STRING | no (post-match) | Final score text; contains RET (retired), W/O (walkover), DEF (default) (text here; typed in 04) |
| `best_of` | STRING | yes | Maximum number of sets (text here; typed in 04) |
| `round` | STRING | yes | Round: R128, R64, R32, R16, QF, SF, F (RR = round robin, excluded in 04) (text here; typed in 04) |
| `minutes` | STRING | no (post-match) | Match length in minutes (recorded from 2016 on) (text here; typed in 04) |
| `w_ace` | STRING | no (post-match) | Winner: aces (text here; typed in 04) |
| `w_df` | STRING | no (post-match) | Winner: double faults (text here; typed in 04) |
| `w_svpt` | STRING | no (post-match) | Winner: serve points played (text here; typed in 04) |
| `w_1stIn` | STRING | no (post-match) | Winner: first serves in (text here; typed in 04) |
| `w_1stWon` | STRING | no (post-match) | Winner: points won on first serve (text here; typed in 04) |
| `w_2ndWon` | STRING | no (post-match) | Winner: points won on second serve (text here; typed in 04) |
| `w_SvGms` | STRING | no (post-match) | Winner: service games played (text here; typed in 04) |
| `w_bpSaved` | STRING | no (post-match) | Winner: break points saved (text here; typed in 04) |
| `w_bpFaced` | STRING | no (post-match) | Winner: break points faced (text here; typed in 04) |
| `l_ace` | STRING | no (post-match) | Loser: aces (text here; typed in 04) |
| `l_df` | STRING | no (post-match) | Loser: double faults (text here; typed in 04) |
| `l_svpt` | STRING | no (post-match) | Loser: serve points played (text here; typed in 04) |
| `l_1stIn` | STRING | no (post-match) | Loser: first serves in (text here; typed in 04) |
| `l_1stWon` | STRING | no (post-match) | Loser: points won on first serve (text here; typed in 04) |
| `l_2ndWon` | STRING | no (post-match) | Loser: points won on second serve (text here; typed in 04) |
| `l_SvGms` | STRING | no (post-match) | Loser: service games played (text here; typed in 04) |
| `l_bpSaved` | STRING | no (post-match) | Loser: break points saved (text here; typed in 04) |
| `l_bpFaced` | STRING | no (post-match) | Loser: break points faced (text here; typed in 04) |
| `winner_rank` | STRING | yes, but the winner/loser side reveals the result | Winner: WTA ranking at tourney_date (text here; typed in 04) |
| `winner_rank_points` | STRING | yes, but the winner/loser side reveals the result | Winner: WTA ranking points at tourney_date (text here; typed in 04) |
| `loser_rank` | STRING | yes, but the winner/loser side reveals the result | Loser: WTA ranking at tourney_date (text here; typed in 04) |
| `loser_rank_points` | STRING | yes, but the winner/loser side reveals the result | Loser: WTA ranking points at tourney_date (text here; typed in 04) |

## tennis_clean.matches

Typed matches, levels G/PM/P/I, no round-robin events. One row per match, winner/loser layout.

| column | type | known before match | description |
|---|---|---|---|
| `match_id` | STRING | id | Match ID: tourney_id + '-' + match_num. Unique per match |
| `tourney_id` | STRING | yes | Tournament edition ID: season year + tournament code |
| `tourney_name` | STRING | yes | Tournament name as in the source |
| `name_key` | STRING | yes | Lower-cased, trimmed tourney_name; join key to the venue tables |
| `tourney_date` | DATE | yes | Tournament start date (raw: text YYYYMMDD). Not the match date |
| `season` | INTEGER | yes | Season = year in tourney_id. Late-December events belong to the next season |
| `tourney_level` | STRING | yes | Level: G = Grand Slam, PM = Premier Mandatory, P = Premier, I = International. Raw also has D, O, W, 35+H, 50+H (excluded in 04) |
| `surface` | STRING | yes | Court surface: hard, clay, grass (lower-cased from 04 on) |
| `is_walkover` | BOOLEAN | no (post-match) | TRUE if the score contains W/O (no tennis played) |
| `is_retirement` | BOOLEAN | no (post-match) | TRUE if the score contains RET |
| `is_default` | BOOLEAN | no (post-match) | TRUE if the score contains DEF |
| `draw_size` | INTEGER | yes | Number of players in the main draw |
| `best_of` | INTEGER | yes | Maximum number of sets |
| `match_num` | INTEGER | id | Match number within the tournament |
| `winner_id` | INTEGER | yes, but the winner/loser side reveals the result | Winner: player ID (stable across seasons) |
| `winner_seed` | INTEGER | yes, but the winner/loser side reveals the result | Winner: seed number (NULL = unseeded; raw may hold entry codes) |
| `winner_ht` | INTEGER | yes, but the winner/loser side reveals the result | Winner: height, cm |
| `loser_id` | INTEGER | yes, but the winner/loser side reveals the result | Loser: player ID (stable across seasons) |
| `loser_seed` | INTEGER | yes, but the winner/loser side reveals the result | Loser: seed number (NULL = unseeded; raw may hold entry codes) |
| `loser_ht` | INTEGER | yes, but the winner/loser side reveals the result | Loser: height, cm |
| `minutes` | INTEGER | no (post-match) | Match length in minutes (recorded from 2016 on) |
| `w_ace` | INTEGER | no (post-match) | Winner: aces |
| `w_df` | INTEGER | no (post-match) | Winner: double faults |
| `w_svpt` | INTEGER | no (post-match) | Winner: serve points played |
| `w_1stIn` | INTEGER | no (post-match) | Winner: first serves in |
| `w_1stWon` | INTEGER | no (post-match) | Winner: points won on first serve |
| `w_2ndWon` | INTEGER | no (post-match) | Winner: points won on second serve |
| `w_SvGms` | INTEGER | no (post-match) | Winner: service games played |
| `w_bpSaved` | INTEGER | no (post-match) | Winner: break points saved |
| `w_bpFaced` | INTEGER | no (post-match) | Winner: break points faced |
| `l_ace` | INTEGER | no (post-match) | Loser: aces |
| `l_df` | INTEGER | no (post-match) | Loser: double faults |
| `l_svpt` | INTEGER | no (post-match) | Loser: serve points played |
| `l_1stIn` | INTEGER | no (post-match) | Loser: first serves in |
| `l_1stWon` | INTEGER | no (post-match) | Loser: points won on first serve |
| `l_2ndWon` | INTEGER | no (post-match) | Loser: points won on second serve |
| `l_SvGms` | INTEGER | no (post-match) | Loser: service games played |
| `l_bpSaved` | INTEGER | no (post-match) | Loser: break points saved |
| `l_bpFaced` | INTEGER | no (post-match) | Loser: break points faced |
| `winner_rank` | INTEGER | yes, but the winner/loser side reveals the result | Winner: WTA ranking at tourney_date |
| `winner_rank_points` | INTEGER | yes, but the winner/loser side reveals the result | Winner: WTA ranking points at tourney_date |
| `loser_rank` | INTEGER | yes, but the winner/loser side reveals the result | Loser: WTA ranking at tourney_date |
| `loser_rank_points` | INTEGER | yes, but the winner/loser side reveals the result | Loser: WTA ranking points at tourney_date |
| `winner_age` | FLOAT | yes, but the winner/loser side reveals the result | Winner: age in years at tourney_date |
| `loser_age` | FLOAT | yes, but the winner/loser side reveals the result | Loser: age in years at tourney_date |
| `winner_name` | STRING | yes, but the winner/loser side reveals the result | Winner: player name |
| `winner_hand` | STRING | yes, but the winner/loser side reveals the result | Winner: playing hand: R, L, U = unknown |
| `winner_ioc` | STRING | yes, but the winner/loser side reveals the result | Winner: country, 3-letter IOC code |
| `loser_name` | STRING | yes, but the winner/loser side reveals the result | Loser: player name |
| `loser_hand` | STRING | yes, but the winner/loser side reveals the result | Loser: playing hand: R, L, U = unknown |
| `loser_ioc` | STRING | yes, but the winner/loser side reveals the result | Loser: country, 3-letter IOC code |
| `score` | STRING | no (post-match) | Final score text; contains RET (retired), W/O (walkover), DEF (default) |
| `round` | STRING | yes | Round: R128, R64, R32, R16, QF, SF, F (RR = round robin, excluded in 04) |
| `winner_entry` | STRING | yes, but the winner/loser side reveals the result | Winner: entry: Q qualifier, WC wildcard, LL lucky loser, PR protected ranking, SE special exempt, ALT alternate; NULL = direct entry |
| `loser_entry` | STRING | yes, but the winner/loser side reveals the result | Loser: entry: Q qualifier, WC wildcard, LL lucky loser, PR protected ranking, SE special exempt, ALT alternate; NULL = direct entry |

## tennis_clean.matches_dated

tennis_clean.matches plus the event format and a window of possible match days.

| column | type | known before match | description |
|---|---|---|---|
| `match_id` | STRING | id | Match ID: tourney_id + '-' + match_num. Unique per match |
| `tourney_id` | STRING | yes | Tournament edition ID: season year + tournament code |
| `tourney_name` | STRING | yes | Tournament name as in the source |
| `name_key` | STRING | yes | Lower-cased, trimmed tourney_name; join key to the venue tables |
| `tourney_date` | DATE | yes | Tournament start date (raw: text YYYYMMDD). Not the match date |
| `season` | INTEGER | yes | Season = year in tourney_id. Late-December events belong to the next season |
| `tourney_level` | STRING | yes | Level: G = Grand Slam, PM = Premier Mandatory, P = Premier, I = International. Raw also has D, O, W, 35+H, 50+H (excluded in 04) |
| `surface` | STRING | yes | Court surface: hard, clay, grass (lower-cased from 04 on) |
| `is_walkover` | BOOLEAN | no (post-match) | TRUE if the score contains W/O (no tennis played) |
| `is_retirement` | BOOLEAN | no (post-match) | TRUE if the score contains RET |
| `is_default` | BOOLEAN | no (post-match) | TRUE if the score contains DEF |
| `draw_size` | INTEGER | yes | Number of players in the main draw |
| `best_of` | INTEGER | yes | Maximum number of sets |
| `match_num` | INTEGER | id | Match number within the tournament |
| `winner_id` | INTEGER | yes, but the winner/loser side reveals the result | Winner: player ID (stable across seasons) |
| `winner_seed` | INTEGER | yes, but the winner/loser side reveals the result | Winner: seed number (NULL = unseeded; raw may hold entry codes) |
| `winner_ht` | INTEGER | yes, but the winner/loser side reveals the result | Winner: height, cm |
| `loser_id` | INTEGER | yes, but the winner/loser side reveals the result | Loser: player ID (stable across seasons) |
| `loser_seed` | INTEGER | yes, but the winner/loser side reveals the result | Loser: seed number (NULL = unseeded; raw may hold entry codes) |
| `loser_ht` | INTEGER | yes, but the winner/loser side reveals the result | Loser: height, cm |
| `minutes` | INTEGER | no (post-match) | Match length in minutes (recorded from 2016 on) |
| `w_ace` | INTEGER | no (post-match) | Winner: aces |
| `w_df` | INTEGER | no (post-match) | Winner: double faults |
| `w_svpt` | INTEGER | no (post-match) | Winner: serve points played |
| `w_1stIn` | INTEGER | no (post-match) | Winner: first serves in |
| `w_1stWon` | INTEGER | no (post-match) | Winner: points won on first serve |
| `w_2ndWon` | INTEGER | no (post-match) | Winner: points won on second serve |
| `w_SvGms` | INTEGER | no (post-match) | Winner: service games played |
| `w_bpSaved` | INTEGER | no (post-match) | Winner: break points saved |
| `w_bpFaced` | INTEGER | no (post-match) | Winner: break points faced |
| `l_ace` | INTEGER | no (post-match) | Loser: aces |
| `l_df` | INTEGER | no (post-match) | Loser: double faults |
| `l_svpt` | INTEGER | no (post-match) | Loser: serve points played |
| `l_1stIn` | INTEGER | no (post-match) | Loser: first serves in |
| `l_1stWon` | INTEGER | no (post-match) | Loser: points won on first serve |
| `l_2ndWon` | INTEGER | no (post-match) | Loser: points won on second serve |
| `l_SvGms` | INTEGER | no (post-match) | Loser: service games played |
| `l_bpSaved` | INTEGER | no (post-match) | Loser: break points saved |
| `l_bpFaced` | INTEGER | no (post-match) | Loser: break points faced |
| `winner_rank` | INTEGER | yes, but the winner/loser side reveals the result | Winner: WTA ranking at tourney_date |
| `winner_rank_points` | INTEGER | yes, but the winner/loser side reveals the result | Winner: WTA ranking points at tourney_date |
| `loser_rank` | INTEGER | yes, but the winner/loser side reveals the result | Loser: WTA ranking at tourney_date |
| `loser_rank_points` | INTEGER | yes, but the winner/loser side reveals the result | Loser: WTA ranking points at tourney_date |
| `winner_age` | FLOAT | yes, but the winner/loser side reveals the result | Winner: age in years at tourney_date |
| `loser_age` | FLOAT | yes, but the winner/loser side reveals the result | Loser: age in years at tourney_date |
| `winner_name` | STRING | yes, but the winner/loser side reveals the result | Winner: player name |
| `winner_hand` | STRING | yes, but the winner/loser side reveals the result | Winner: playing hand: R, L, U = unknown |
| `winner_ioc` | STRING | yes, but the winner/loser side reveals the result | Winner: country, 3-letter IOC code |
| `loser_name` | STRING | yes, but the winner/loser side reveals the result | Loser: player name |
| `loser_hand` | STRING | yes, but the winner/loser side reveals the result | Loser: playing hand: R, L, U = unknown |
| `loser_ioc` | STRING | yes, but the winner/loser side reveals the result | Loser: country, 3-letter IOC code |
| `score` | STRING | no (post-match) | Final score text; contains RET (retired), W/O (walkover), DEF (default) |
| `round` | STRING | yes | Round: R128, R64, R32, R16, QF, SF, F (RR = round robin, excluded in 04) |
| `winner_entry` | STRING | yes, but the winner/loser side reveals the result | Winner: entry: Q qualifier, WC wildcard, LL lucky loser, PR protected ranking, SE special exempt, ALT alternate; NULL = direct entry |
| `loser_entry` | STRING | yes, but the winner/loser side reveals the result | Loser: entry: Q qualifier, WC wildcard, LL lucky loser, PR protected ranking, SE special exempt, ALT alternate; NULL = direct entry |
| `event_format` | STRING | yes | SLAM, TWO_WEEK, LONG_WEEK or ONE_WEEK (from level and the first round played) |
| `day_min` | INTEGER | yes (estimate) | Earliest day (offset from tourney_date) the match could have been played |
| `day_max` | INTEGER | yes (estimate) | Latest day (offset from tourney_date) the match could have been played |
| `match_date_min` | DATE | yes (estimate) | Earliest possible match date = tourney_date + day_min |
| `match_date_max` | DATE | yes (estimate) | Latest possible match date = tourney_date + day_max |

## tennis_clean.venue_name_map

Tournament name key -> place searched for in the geocoding API.

| column | type | known before match | description |
|---|---|---|---|
| `name_key` | STRING | yes | Lower-cased, trimmed tourney_name; join key to the venue tables |
| `search_name` | STRING | yes | Place name searched for in the geocoding API |

## tennis_clean.venue_locations

One row per place: coordinates and the geocoding result chosen.

| column | type | known before match | description |
|---|---|---|---|
| `search_name` | STRING | yes | Place name searched for in the geocoding API |
| `place` | STRING | yes | Place name returned by the geocoding API |
| `region` | STRING | yes | Region / state of the place (geocoding admin1) |
| `country_code` | STRING | yes | Country of the place (ISO 3166-1 alpha-2) |
| `latitude` | FLOAT | yes | Latitude of the place, degrees |
| `longitude` | FLOAT | yes | Longitude of the place, degrees |
| `elevation_m` | FLOAT | yes | Elevation of the place, metres |
| `timezone` | STRING | yes | IANA time zone of the place |
| `geonames_id` | set by the pandas upload | id | GeoNames ID of the chosen result |
| `population` | set by the pandas upload | yes | Population of the place (geocoding API) |
| `decision` | STRING | metadata | How the result was chosen: top result, re-searched, or picked by hand |

## tennis_clean.tournament_editions

One row per tournament edition, with coordinates and the weather window fetched.

| column | type | known before match | description |
|---|---|---|---|
| `tourney_id` | STRING | yes | Tournament edition ID: season year + tournament code |
| `name_key` | STRING | yes | Lower-cased, trimmed tourney_name; join key to the venue tables |
| `search_name` | STRING | yes | Place name searched for in the geocoding API |
| `place` | STRING | yes | Place name returned by the geocoding API |
| `country_code` | STRING | yes | Country of the place (ISO 3166-1 alpha-2) |
| `tourney_level` | STRING | yes | Level: G = Grand Slam, PM = Premier Mandatory, P = Premier, I = International. Raw also has D, O, W, 35+H, 50+H (excluded in 04) |
| `draw_size` | INTEGER | yes | Number of players in the main draw |
| `event_format` | STRING | yes | SLAM, TWO_WEEK, LONG_WEEK or ONE_WEEK (from level and the first round played) |
| `start_date` | DATE | yes | Weather window start = tourney_date |
| `end_date` | DATE | yes | Weather window end = last possible match day + 1, cut back for the archive delay |
| `last_match_day` | DATE | yes (estimate) | Latest possible match day of the edition |
| `latitude` | FLOAT | yes | Latitude of the place, degrees |
| `longitude` | FLOAT | yes | Longitude of the place, degrees |
| `elevation_m` | FLOAT | yes | Elevation of the place, metres |
| `timezone` | STRING | yes | IANA time zone of the place |
| `n_matches` | INTEGER | metadata | Number of matches in the edition |

## tennis_clean.matches_ab

One row per match in player A vs player B layout, label a_won. Columns starting post_ are only known after the match.

| column | type | known before match | description |
|---|---|---|---|
| `match_id` | STRING | id | Match ID: tourney_id + '-' + match_num. Unique per match |
| `tourney_id` | STRING | yes | Tournament edition ID: season year + tournament code |
| `tourney_name` | STRING | yes | Tournament name as in the source |
| `name_key` | STRING | yes | Lower-cased, trimmed tourney_name; join key to the venue tables |
| `tourney_date` | DATE | yes | Tournament start date (raw: text YYYYMMDD). Not the match date |
| `season` | INTEGER | yes | Season = year in tourney_id. Late-December events belong to the next season |
| `tourney_level` | STRING | yes | Level: G = Grand Slam, PM = Premier Mandatory, P = Premier, I = International. Raw also has D, O, W, 35+H, 50+H (excluded in 04) |
| `surface` | STRING | yes | Court surface: hard, clay, grass (lower-cased from 04 on) |
| `draw_size` | INTEGER | yes | Number of players in the main draw |
| `best_of` | INTEGER | yes | Maximum number of sets |
| `round` | STRING | yes | Round: R128, R64, R32, R16, QF, SF, F (RR = round robin, excluded in 04) |
| `event_format` | STRING | yes | SLAM, TWO_WEEK, LONG_WEEK or ONE_WEEK (from level and the first round played) |
| `match_date_min` | DATE | yes (estimate) | Earliest possible match date = tourney_date + day_min |
| `match_date_max` | DATE | yes (estimate) | Latest possible match date = tourney_date + day_max |
| `a_id` | INTEGER | yes | Player A: player ID (stable across seasons) |
| `b_id` | INTEGER | yes | Player B: player ID (stable across seasons) |
| `a_name` | STRING | yes | Player A: player name |
| `b_name` | STRING | yes | Player B: player name |
| `a_seed` | INTEGER | yes | Player A: seed number (NULL = unseeded; raw may hold entry codes) |
| `b_seed` | INTEGER | yes | Player B: seed number (NULL = unseeded; raw may hold entry codes) |
| `a_entry` | STRING | yes | Player A: entry: Q qualifier, WC wildcard, LL lucky loser, PR protected ranking, SE special exempt, ALT alternate; NULL = direct entry |
| `b_entry` | STRING | yes | Player B: entry: Q qualifier, WC wildcard, LL lucky loser, PR protected ranking, SE special exempt, ALT alternate; NULL = direct entry |
| `a_hand` | STRING | yes | Player A: playing hand: R, L, U = unknown |
| `b_hand` | STRING | yes | Player B: playing hand: R, L, U = unknown |
| `a_ht` | INTEGER | yes | Player A: height, cm |
| `b_ht` | INTEGER | yes | Player B: height, cm |
| `a_ioc` | STRING | yes | Player A: country, 3-letter IOC code |
| `b_ioc` | STRING | yes | Player B: country, 3-letter IOC code |
| `a_age` | FLOAT | yes | Player A: age in years at tourney_date |
| `b_age` | FLOAT | yes | Player B: age in years at tourney_date |
| `a_rank` | INTEGER | yes | Player A: WTA ranking at tourney_date |
| `b_rank` | INTEGER | yes | Player B: WTA ranking at tourney_date |
| `a_rank_points` | INTEGER | yes | Player A: WTA ranking points at tourney_date |
| `b_rank_points` | INTEGER | yes | Player B: WTA ranking points at tourney_date |
| `post_a_ace` | INTEGER | no (post-match) | Player A: aces |
| `post_b_ace` | INTEGER | no (post-match) | Player B: aces |
| `post_a_df` | INTEGER | no (post-match) | Player A: double faults |
| `post_b_df` | INTEGER | no (post-match) | Player B: double faults |
| `post_a_svpt` | INTEGER | no (post-match) | Player A: serve points played |
| `post_b_svpt` | INTEGER | no (post-match) | Player B: serve points played |
| `post_a_1stIn` | INTEGER | no (post-match) | Player A: first serves in |
| `post_b_1stIn` | INTEGER | no (post-match) | Player B: first serves in |
| `post_a_1stWon` | INTEGER | no (post-match) | Player A: points won on first serve |
| `post_b_1stWon` | INTEGER | no (post-match) | Player B: points won on first serve |
| `post_a_2ndWon` | INTEGER | no (post-match) | Player A: points won on second serve |
| `post_b_2ndWon` | INTEGER | no (post-match) | Player B: points won on second serve |
| `post_a_SvGms` | INTEGER | no (post-match) | Player A: service games played |
| `post_b_SvGms` | INTEGER | no (post-match) | Player B: service games played |
| `post_a_bpSaved` | INTEGER | no (post-match) | Player A: break points saved |
| `post_b_bpSaved` | INTEGER | no (post-match) | Player B: break points saved |
| `post_a_bpFaced` | INTEGER | no (post-match) | Player A: break points faced |
| `post_b_bpFaced` | INTEGER | no (post-match) | Player B: break points faced |
| `a_won` | INTEGER | label | LABEL: 1 if player A won, 0 otherwise |
| `post_score` | STRING | no (post-match) | Final score text (see score) |
| `post_minutes` | INTEGER | no (post-match) | Match length in minutes (from 2016 on) |
| `post_is_walkover` | BOOLEAN | no (post-match) | TRUE if walkover (no tennis played); such rows are excluded from modelling |
| `post_is_retirement` | BOOLEAN | no (post-match) | TRUE if a player retired |
| `post_is_default` | BOOLEAN | no (post-match) | TRUE if a player was defaulted |

## tennis_features.match_splits

Split per match (by season), and whether the row can be used for modelling.

| column | type | known before match | description |
|---|---|---|---|
| `match_id` | STRING | id | Match ID: tourney_id + '-' + match_num. Unique per match |
| `tourney_id` | STRING | yes | Tournament edition ID: season year + tournament code |
| `tourney_date` | DATE | yes | Tournament start date (raw: text YYYYMMDD). Not the match date |
| `season` | INTEGER | yes | Season = year in tourney_id. Late-December events belong to the next season |
| `split` | STRING | metadata | warmup (2010-15), train (2016-22), dev (2023-24), test (2025), holdout_2026 |
| `modelling_ok` | BOOLEAN | metadata | FALSE for walkovers: kept, but excluded from fitting and evaluation |
| `split_version` | STRING | metadata | Version of the split definition |

## Model data release (Parquet, `processed/model_data/release=v1/split=<name>/`)

All columns of `tennis_clean.matches_ab`, plus `split` (STRING) and `modelling_ok` (BOOLEAN). One folder per split: train, dev, test, holdout_2026.
