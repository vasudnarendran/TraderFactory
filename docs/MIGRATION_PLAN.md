# Migration Plan

This repo scaffold is based on real assets already present in the current project.

## Stage 1: Copy Knowledge And References

Status: completed in the initial scaffold.

Bring in first:

- strategy research
- execution research docs
- key reference bots
- architecture and workflow docs

## Stage 2: Extract Reusable Engines

Status: largely completed for the headless stack.

Migrate:

- deterministic backtester from `Backtest_failed_Python/run_backtest.py`
- headless Monte Carlo robustness from the research workflow
- Monte Carlo viewer from `MonteCarloBacktester/monte_carlo_viewer/`
- analyzers from `Analysis/`
- CMA-ES and sweep tooling from `Analysis/`
- probe framework from `Research/execution_probes/`

Remaining gaps in this stage:

- Monte Carlo viewer/dashboard UI
- richer sweep tooling beyond the current CMA-ES engine
- historical probe bot examples as reusable templates

## Stage 3: Normalize Interfaces

Status: completed for the main CLI surface.

Define standard interfaces for:

- `run_deterministic`
- `run_monte_carlo`
- `run_optimizer`
- `run_official_postmortem`
- `run_probe`

## Stage 4: Add Generation

Status: baseline scaffolding completed; richer generation still open.

Add baseline project generation from:

- `CompetitionSpec`
- `ProductSpec`
- selected strategy capabilities

Current generation already includes:

- round planning
- baseline trader project scaffolding
- probe workspace scaffolding

Still open in generation:

- capability-to-sleeve code synthesis
- optimizer and probe config generation inside projects
- stronger templates by product family

## Stage 5: Add Richer Mechanic Families

Status: planned, not implemented.

Once the base system works well:

- options
- baskets
- conversions
- informed-flow modules
