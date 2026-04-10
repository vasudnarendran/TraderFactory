# Engine Layer

This document describes the first working engine layer inside `TraderFactory`.

Important status note:

- deterministic replay is self-contained in this repo and smoke-tested
- CMA-ES optimization is self-contained in this repo and smoke-tested
- Monte Carlo robustness is self-contained in this repo and smoke-tested
- official diagnostics are self-contained in this repo and smoke-tested

So the current local engine stack covers:

- deterministic replay
- Monte Carlo robustness
- CMA-ES optimization
- official diagnostics

The main remaining simulation-related migration is the old viewer/dashboard layer, not the headless robustness engine.

## 1. Deterministic Replay

Engine entry points:

- [trader_factory/simulation/deterministic.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/simulation/deterministic.py)
- [trader_factory/simulation/internal_backtest.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/simulation/internal_backtest.py)
- [trader_factory/core/datamodel.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/core/datamodel.py)

Current CLI:

```bash
python3 -m trader_factory.cli deterministic /path/to/Trader.py --day -1
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

- viewer/dashboard UI
- browser/server tooling
- release/distribution helpers from the old `MonteCarloBacktester` bundle

## 4. Official Diagnostics

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

## 5. What Still Needs Migration

The current engine layer is no longer purely a wrapper layer.

What is already local:

- deterministic replay
- Monte Carlo robustness
- CMA-ES optimization
- official diagnostics

What still needs migration:

1. Monte Carlo viewer/dashboard tooling
2. sweep tooling and additional optimization objectives
3. generated trader-project creation on top of the engine layer

That is the remaining path from a solid local toolkit to a full development factory.
