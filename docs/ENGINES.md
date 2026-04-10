# Engine Layer

This document describes the first working engine layer inside `TraderFactory`.

Important status note:

- deterministic replay is self-contained in this repo and smoke-tested
- CMA-ES optimization is self-contained in this repo and smoke-tested
- Monte Carlo robustness is self-contained in this repo and smoke-tested
- Monte Carlo viewer is self-contained in this repo
- execution-probe scaffolding is self-contained in this repo
- official diagnostics are self-contained in this repo and smoke-tested
- baseline project generation is self-contained in this repo

## Data And Inputs

What you need to run the engines:

- deterministic replay and Monte Carlo:
  - a trader Python file
  - replay CSVs named like `prices_<dataset_tag>_day_<day>.csv` and `trades_<dataset_tag>_day_<day>.csv`
- official diagnostics:
  - official `.log`
  - sometimes official `.json`
- probe scaffolding:
  - a baseline trader Python file

Replay data resolution order:

1. `TraderFactory/data/`
2. the legacy sibling path `../Prosperity/Data/`
3. an explicit `--data-root` override always wins

The legacy sibling path is only a fallback for convenience. The intended standalone home for replay data is [data/README.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/data/README.md).

So the current local engine stack covers:

- deterministic replay
- Monte Carlo robustness
- Monte Carlo viewer
- CMA-ES optimization
- official diagnostics

## 1. Deterministic Replay

Engine entry points:

- [trader_factory/simulation/deterministic.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/simulation/deterministic.py)
- [trader_factory/simulation/internal_backtest.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/simulation/internal_backtest.py)
- [trader_factory/core/datamodel.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/core/datamodel.py)

Current CLI:

```bash
python3 -m trader_factory.cli deterministic /path/to/Trader.py --day -1
python3 -m trader_factory.cli deterministic /path/to/Trader.py --day -1 --data-root /path/to/data --dataset-tag round_0
```

What it returns:

- a TraderFactory output directory under `generated/runs/deterministic/`
- `summary.txt`
- `step_log.csv`
- `fills.csv`
- `product_log.csv`
- parsed final total PnL

What was validated:

- replay through [Traderv52.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Bots/Traderv52.py)
- final total PnL parsed successfully as `15081.0` on day `-1`

Important behavior note from the current local engine:

- it resets positions, cash, pending orders, and `traderData` on day boundaries
- but it does not recreate the trader object mid-run

Working implication:

- generated traders should prefer explicit `traderData` over hidden instance state when reproducibility matters

## 2. Optimization

Engine entry points:

- [trader_factory/optimization/cmaes.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/optimization/cmaes.py)

Current CLI:

```bash
python3 -m trader_factory.cli cmaes configs/examples/v52_tight_cmaes.json
```

What it returns:

- a TraderFactory output directory under `generated/optimization/`
- `*_best.json`
- `*_report.md`
- materialized best bot source under `bots/`

What was validated:

- the v52-style TOMATOES tuning problem can now be run from TraderFactory directly
- optimization uses the local deterministic replay engine, not the old analysis script

Important scope note:

- the current optimizer is a config-driven regularized CMA-ES
- it supports named dict-block parameters and class constants
- sweep tooling and richer objectives are still future work

## 3. Monte Carlo

Engine entry points:

- [trader_factory/simulation/monte_carlo.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/simulation/monte_carlo.py)

Current CLI:

```bash
python3 -m trader_factory.cli monte-carlo /path/to/Trader.py
python3 -m trader_factory.cli monte-carlo /path/to/PrimaryTrader.py --compare-bot /path/to/BaselineTrader.py
python3 -m trader_factory.cli monte-carlo /path/to/Trader.py --data-root /path/to/data --dataset-tag round_0
```

Current status:

- the headless robustness engine is local
- it reuses TraderFactory's internal replay model instead of shelling out to the old Monte Carlo CLI
- it writes JSON, markdown, and CSV artifacts under TraderFactory output directories

What was validated:

- a reduced paired run comparing [Traderv52.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Bots/Traderv52.py) vs [Traderv51.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Bots/Traderv51.py)
- output artifacts were written successfully to `/tmp`
- the report schema matches the earlier research workflow shape

What is not yet migrated:

- release/distribution helpers from the old `MonteCarloBacktester` bundle
- a more general viewer schema for arbitrary future product families

## 4. Monte Carlo Viewer

Engine entry points:

- [trader_factory/viewer/monte_carlo.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/viewer/monte_carlo.py)

Current CLI:

```bash
python3 -m trader_factory.cli viewer
python3 -m trader_factory.cli viewer --results-dir /absolute/path/to/extra_results
```

Current status:

- the browser viewer is local
- it scans result roots recursively, so nested `report.json` run folders work
- it can still read older dashboard JSONs if you point it at those directories

Important scope note:

- the viewer is local to `TraderFactory`
- but the current UI is still tuned for the existing Prosperity-style report and dashboard schema
- it is not yet fully generalized for arbitrary future product families

## 5. Official Diagnostics

Engine entry points:

- [trader_factory/diagnostics/official.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/diagnostics/official.py)
- [trader_factory/diagnostics/trade_quality.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/diagnostics/trade_quality.py)
- [trader_factory/diagnostics/boundary_probe.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/diagnostics/boundary_probe.py)
- [trader_factory/diagnostics/passive_ladder.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/diagnostics/passive_ladder.py)
- [trader_factory/diagnostics/aggressive_markout.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/diagnostics/aggressive_markout.py)

Current CLI:

```bash
python3 -m trader_factory.cli official-trade-quality /path/to/run.log --baseline /path/to/baseline.log
python3 -m trader_factory.cli boundary-probe /path/to/run.log
python3 -m trader_factory.cli passive-ladder /path/to/run.log --json-path /path/to/run.json
python3 -m trader_factory.cli aggressive-markout /path/to/run.log --json-path /path/to/run.json
```

What was validated:

- official trade quality wrapper
- boundary probe wrapper
- passive ladder wrapper
- aggressive markout wrapper

They now write results under `TraderFactory/generated/reports/` instead of forcing the user to inspect `Analysis/output/` manually.

## 6. Probe Framework

Engine entry points:

- [trader_factory/probes/specs.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/probes/specs.py)
- [trader_factory/probes/logging.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/probes/logging.py)
- [trader_factory/probes/scaffold.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/probes/scaffold.py)

Current CLI:

```bash
python3 -m trader_factory.cli probe-scaffold boundary /path/to/Traderv52.py
python3 -m trader_factory.cli probe-scaffold aggressive_markout /path/to/Traderv52.py --context range_buy
```

What it returns:

- a research workspace with:
  - `README.md`
  - `probe.json`
  - `submission_probe.py`
  - `notes.md`

Current scope:

- built-in probe types:
  - boundary
  - passive_ladder
  - aggressive_markout
- standardized DIAG event scaffolding
- research workspace generation around a baseline bot

Important limitation:

- this is a framework and scaffold, not an automatic source-to-probe transformer
- actual integration into a baseline submission bot is still intentional manual/agent work

## 7. Project Generation

Engine entry points:

- [trader_factory/generation/project.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/generation/project.py)

Current CLI:

```bash
python3 -m trader_factory.cli scaffold-project configs/examples/prosperity_round0.json
```

What it returns:

- a baseline project directory with:
  - `README.md`
  - `spec.json`
  - `plan.md`
  - `params.py`
  - `trader.py`
  - `notes.md`

Important limitation:

- this is a readable baseline scaffold, not a full strategy autogenerator
- product sleeves still need deliberate implementation work after generation

## 7. What Still Needs Migration

The current engine layer is no longer purely a wrapper layer.

What is already local:

- deterministic replay
- Monte Carlo robustness
- CMA-ES optimization
- execution-probe framework
- official diagnostics
- baseline project generation

What still needs migration:

1. sweep tooling and additional optimization objectives
2. historical probe bot examples as reusable templates
3. richer code generation from capability sets into actual strategy sleeves
4. broader viewer/report-schema generalization for future mechanics

That is the remaining path from a solid local toolkit to a full development factory.
