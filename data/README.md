# Replay Data

`TraderFactory` does not bundle Prosperity market data by default.

To run deterministic replay or Monte Carlo locally, place the round CSV files in this directory using the standard filenames:

- `prices_round_0_day_-2.csv`
- `prices_round_0_day_-1.csv`
- `trades_round_0_day_-2.csv`
- `trades_round_0_day_-1.csv`

Current engine expectations:

- deterministic replay and Monte Carlo look in `TraderFactory/data/` first
- if nothing is present there, they fall back to the legacy sibling path `../Prosperity/Data/`
- you can always override the source explicitly with `--data-root`

This directory is intentionally the default standalone home for replay datasets inside the new repo.
