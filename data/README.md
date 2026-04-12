# Replay Data

`TraderFactory` does not bundle market data by default.

To run deterministic replay or Monte Carlo locally, place replay CSVs in this directory using the standard filename pattern:

- `prices_<dataset_tag>_day_<day>.csv`
- `trades_<dataset_tag>_day_<day>.csv`

Optional observation inputs:

- preferred sidecar name: `observations_<dataset_tag>_day_<day>.csv`
- compatibility alias for plain observations: `plain_observations_<dataset_tag>_day_<day>.csv`
- compatibility alias: `conversion_observations_<dataset_tag>_day_<day>.csv`
- canonical plain-observation sidecar columns:
  - `day,timestamp,product,value`
  - or `day,timestamp,observation_key,value` when the observation key is not the traded product symbol
- canonical conversion-observation sidecar columns:
  - `day,timestamp,product,bid_price,ask_price,transport_fees,export_tariff,import_tariff,sunlight,humidity`
- the replay engines also accept inline observation columns on the `prices_*.csv` rows when the dataset already embeds them
- plain observations can be embedded inline with fields such as `observation_value`, `plain_observation_value`, or `signal_value`

Examples:

- `prices_round_0_day_-2.csv`
- `prices_round_0_day_-1.csv`
- `trades_round_0_day_-2.csv`
- `trades_round_0_day_-1.csv`
- `prices_round_1_day_0.csv`
- `trades_options_day_3.csv`

Current engine expectations:

- deterministic replay and Monte Carlo look in `TraderFactory/data/` first
- if nothing is present there, they fall back to the legacy sibling path `../Prosperity/Data/`
- you can override the source explicitly with `--data-root`
- if a directory contains multiple datasets, pass `--dataset-tag`

This directory is intentionally the default standalone home for replay datasets inside the new repo.
