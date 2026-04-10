# Viewer

`TraderFactory` now includes a local Monte Carlo viewer.

Entry point:

- [trader_factory/viewer/monte_carlo.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/viewer/monte_carlo.py)

CLI:

```bash
python3 -m trader_factory.cli viewer
```

Then open:

```text
http://127.0.0.1:8012
```

## Default Scan Roots

By default, the viewer scans these directory roots recursively:

- `generated/runs/monte_carlo/`
- `generated/dashboards/`

This recursive scan is important because current Monte Carlo outputs are stored as nested run folders containing:

- `report.json`
- `report.md`
- `sample_totals.csv`
- `day_results.csv`

## Custom Result Roots

You can add one or more extra result roots:

```bash
python3 -m trader_factory.cli viewer \
  --results-dir /absolute/path/to/results \
  --results-dir /absolute/path/to/legacy_dashboards
```

## What The Viewer Supports

- current TraderFactory Monte Carlo report bundles
- companion `sample_totals.csv` and `day_results.csv`
- older dashboard JSONs if you point the viewer at those directories explicitly

## Current Limitation

The current UI is still tuned for the existing Prosperity-style Monte Carlo and dashboard schema.

That means:

- `plausible` and `stress` profiles are first-class in the UI
- some views still assume the current EMERALDS / TOMATOES style reporting shape

So the viewer is fully local to `TraderFactory`, but not yet fully generalized to arbitrary future product families.

## Why It Still Matters

Even with that limitation, the viewer already solves the main workflow problem:

- browse saved Monte Carlo runs quickly
- compare candidates against the current baseline
- inspect sample-level robustness without leaving the repo
