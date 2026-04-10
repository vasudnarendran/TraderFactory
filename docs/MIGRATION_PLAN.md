# Migration Plan

This repo scaffold is based on real assets already present in the current project.

## Stage 1: Copy Knowledge And References

Bring in first:

- strategy research
- execution research docs
- key reference bots
- architecture and workflow docs

## Stage 2: Extract Reusable Engines

Migrate:

- deterministic backtester from `Backtest_failed_Python/run_backtest.py`
- headless Monte Carlo robustness from the research workflow
- Monte Carlo viewer from `MonteCarloBacktester/monte_carlo_viewer/`
- analyzers from `Analysis/`
- CMA-ES and sweep tooling from `Analysis/`

## Stage 3: Normalize Interfaces

Define standard interfaces for:

- `run_deterministic`
- `run_monte_carlo`
- `run_optimizer`
- `run_official_postmortem`
- `run_probe`

## Stage 4: Add Generation

Add baseline project generation from:

- `CompetitionSpec`
- `ProductSpec`
- selected strategy capabilities

## Stage 5: Add Richer Mechanic Families

Once the base system works well:

- options
- baskets
- conversions
- informed-flow modules
