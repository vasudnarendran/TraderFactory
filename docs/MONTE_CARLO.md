# Monte Carlo

`TraderFactory` now includes a local headless Monte Carlo robustness engine.

Entry point:

- [trader_factory/simulation/monte_carlo.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/simulation/monte_carlo.py)

CLI:

```bash
python3 -m trader_factory.cli monte-carlo /absolute/path/to/Trader.py
```

Comparison run:

```bash
python3 -m trader_factory.cli monte-carlo \
  /absolute/path/to/PrimaryTrader.py \
  --compare-bot /absolute/path/to/BaselineTrader.py
```

Reduced smoke run:

```bash
python3 -m trader_factory.cli monte-carlo \
  /absolute/path/to/PrimaryTrader.py \
  --compare-bot /absolute/path/to/BaselineTrader.py \
  --families original_noise bootstrap_path \
  --samples-per-family 1 \
  --output-dir /tmp/traderfactory_mc_smoke
```

## What The Engine Does

The current engine is the headless robustness harness migrated from the project research workflow.

It currently supports:

- baseline replay on selected historical days
- block-bootstrap path perturbations
- passive-fill degradation
- aggressive slippage perturbations
- paired bot-vs-bot comparison
- JSON, markdown, and CSV artifact output

It does not depend on the legacy `prosperity4mcbt` CLI for headless runs.

## Scenario Families

Built-in families:

- `original_noise`
- `bootstrap_path`
- `bootstrap_balanced`
- `bootstrap_stress`

Built-in profiles:

- `plausible`
- `stress`
- `all`

Quick presets:

- `--quick`
  - defaults to the `plausible` profile if no families are specified
  - lowers `samples-per-family` to `2` if left at the default
- `--heavy`
  - defaults to the `all` profile if no families are specified
  - raises `samples-per-family` to `8` if left at the default

## Output Layout

By default, outputs go to:

```text
generated/runs/monte_carlo/<bot_stem>/
generated/runs/monte_carlo/<primary_stem>_vs_<compare_stem>/
```

Artifacts:

- `report.json`
- `report.md`
- `day_results.csv`
- `sample_totals.csv`

## Current Scope

What is already local to `TraderFactory`:

- scenario generation
- bootstrap/noise replay
- paired comparison
- report generation

The browser viewer is now local too:

- [docs/VIEWER.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/VIEWER.md)

What is still not migrated:

- old release-check / distribution tooling from `MonteCarloBacktester`
- a more general viewer/report schema for arbitrary future product families

Those are separate from the headless robustness engine and should stay separate in future migration work.
