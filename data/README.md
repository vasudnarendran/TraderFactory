# Replay Data

`TraderFactory` does not bundle market data by default.

To run deterministic replay or Monte Carlo locally, place replay CSVs in this directory using the standard filename pattern:

- `prices_<dataset_tag>_day_<day>.csv`
- `trades_<dataset_tag>_day_<day>.csv`

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
