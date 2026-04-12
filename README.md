# TraderFactory

`TraderFactory` is meant to become the reusable development system behind future Prosperity rounds.

Instead of rebuilding the entire workflow for each round by hand, this repo is intended to hold the reusable parts of the process:

- product and mechanic specification
- baseline trader generation
- deterministic backtesting
- Monte Carlo robustness testing
- parameter optimization
- official-log analysis
- execution probes
- research documentation
- agent handoff conventions

The core design idea is simple:

- describe the products and mechanics first
- let the repo suggest relevant strategy families
- generate a readable baseline project
- optimize and diagnose from there

This repo is not yet the finished factory.
It is the first grounded scaffold built from the real work already done in:

- [Prosperity](/Users/vasudravinarendran/Documents/Prosperity/Prosperity)
- [MyProsperity](/Users/vasudravinarendran/Documents/Prosperity/MyProsperity)

Those repos are provenance, not prerequisites.
This repo is intended to stand on its own once you provide:

- a competition spec
- replay CSVs
- official `.log` / `.json` artifacts when doing postmortems

In practice, the target operating model is agent-assisted:

- TraderFactory should absorb the repetitive mechanical work
- the agent should spend tokens on justified reasoning, ambiguity resolution, and design decisions
- unknown mechanics should stay explicit instead of being guessed away

So the README is split into two parts:

1. what already exists in this scaffold right now
2. what the full intended workflow is

## Current Status

The following pieces are already present in this repo scaffold:

- a core spec schema in [trader_factory/core/specs.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/core/specs.py)
- a strategy capability registry in [trader_factory/core/registry.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/core/registry.py)
- a mechanic interpretation and fallback layer in [trader_factory/core/mapping.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/core/mapping.py)
- a structured spec-validation layer in [trader_factory/core/validation.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/core/validation.py)
- a round-brief extraction layer in [trader_factory/intake/briefs.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/intake/briefs.py)
- a structured strategy-family taxonomy in [docs/STRATEGY_TAXONOMY.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/STRATEGY_TAXONOMY.md)
- a baseline planning layer in [trader_factory/generation/bootstrap.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/generation/bootstrap.py)
- a minimal CLI in [trader_factory/cli.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/cli.py)
- a workflow definition in [trader_factory/workflows/modes.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/workflows/modes.py)
- a local CMA-ES optimization engine in [trader_factory/optimization/cmaes.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/optimization/cmaes.py)
- a local headless Monte Carlo robustness engine in [trader_factory/simulation/monte_carlo.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/simulation/monte_carlo.py)
- a local Monte Carlo viewer in [trader_factory/viewer/monte_carlo.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/viewer/monte_carlo.py)
- a first official submission automation path in [trader_factory/official/imc_prosperity.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/official/imc_prosperity.py)
- a queue-aware official submission workflow in [trader_factory/official/workflow.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/official/workflow.py)
- a development-mode decision pipeline in [trader_factory/workflows/imc_develop.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/workflows/imc_develop.py)
- a persisted baseline-policy layer in [trader_factory/workflows/baselines.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/workflows/baselines.py)
- a persisted gate-policy layer in [trader_factory/workflows/gates.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/workflows/gates.py)
- a reusable execution-probe framework in [trader_factory/probes](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/probes)
- a capability-aware project generator in [trader_factory/generation/project.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/generation/project.py)
- structural-product archetype blueprints in [trader_factory/strategies/blueprints.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/strategies/blueprints.py)
- a reusable basket-pricing helper in [trader_factory/strategies/basket.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/strategies/basket.py)
- a reusable linked-product spread helper in [trader_factory/strategies/spread.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/strategies/spread.py)
- a reusable conversion-reference helper in [trader_factory/strategies/conversion.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/strategies/conversion.py)
- a reusable derivative-pricing helper in [trader_factory/strategies/derivative.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/strategies/derivative.py)
- a reusable participant-flow helper in [trader_factory/strategies/participant.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/strategies/participant.py)
- a reusable external-signal normalization helper in [trader_factory/strategies/signal.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/strategies/signal.py)
- working deterministic replay and diagnostics engines in:
  - [trader_factory/simulation/deterministic.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/simulation/deterministic.py)
  - [trader_factory/simulation/internal_backtest.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/simulation/internal_backtest.py)
  - [trader_factory/simulation/monte_carlo.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/simulation/monte_carlo.py)
  - [trader_factory/diagnostics/official.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/diagnostics/official.py)
  - [trader_factory/diagnostics/trade_quality.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/diagnostics/trade_quality.py)
  - [trader_factory/diagnostics/boundary_probe.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/diagnostics/boundary_probe.py)
  - [trader_factory/diagnostics/passive_ladder.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/diagnostics/passive_ladder.py)
  - [trader_factory/diagnostics/aggressive_markout.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/diagnostics/aggressive_markout.py)
- example competition config in [configs/examples/prosperity_round0.json](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/configs/examples/prosperity_round0.json)
- additional future-mechanic spec examples in [configs/README.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/configs/README.md)
- a trader template in [templates/python_trader/Trader.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/templates/python_trader/Trader.py)
- migration and workflow docs in [docs](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs)

The following major capabilities are not yet fully migrated into this repo, but are documented and intentionally planned:

- historical probe-bot catalog migration beyond the new framework
- richer code generation from capabilities into production-ready trader sleeves
- richer optimization tooling beyond the current CMA-ES engine

## Start Here If You Are New

If you are a new teammate or a new coding agent, read these in order:

1. [README.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/README.md)
2. [docs/WORKFLOW.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/WORKFLOW.md)
3. [docs/TRADER_FACTORY_ARCHITECTURE_FULL.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/TRADER_FACTORY_ARCHITECTURE_FULL.md)
4. [docs/AUTONOMY_CHECKLIST.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/AUTONOMY_CHECKLIST.md)
5. [docs/ROUND_START_CHECKLIST.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/ROUND_START_CHECKLIST.md)
6. [docs/SPEC_INTAKE.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/SPEC_INTAKE.md)
7. [references/SOURCE_MAP.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/references/SOURCE_MAP.md)
8. [docs/STRATEGY_TAXONOMY.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/STRATEGY_TAXONOMY.md)
9. [references/Strategies.txt](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/references/Strategies.txt)
10. [references/PUBLIC_STRATEGY_RESEARCH.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/references/PUBLIC_STRATEGY_RESEARCH.md)
11. [references/execution_probes/DISCOVERIES.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/references/execution_probes/DISCOVERIES.md)
12. [docs/ENGINES.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/ENGINES.md)
13. [docs/OPTIMIZATION.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/OPTIMIZATION.md)
14. [docs/MONTE_CARLO.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/MONTE_CARLO.md)
15. [docs/PROBES.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/PROBES.md)
16. [docs/GENERATION.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/GENERATION.md)
17. [docs/OFFICIAL_AUTOMATION.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/OFFICIAL_AUTOMATION.md)

If you only read one technical reference after this README, read the full architecture doc.

## Setup

Minimum setup:

1. Use Python `3.11+`.
2. Install the package from the repo root:

```bash
python3 -m pip install -e .
```

3. Put replay datasets under [data/README.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/data/README.md), or plan to pass `--data-root`.
4. Keep official submission outputs available for diagnostics:
   - `.log`
   - `.json`
   - optionally the submitted `.py`

Input expectations by command:

- `spec-template`: competition spec JSON template generation
- `brief-template` and `intake-workspace`: structured round-brief JSON generation
- `brief-to-spec`, `plan`, `validate-spec`, and `scaffold-project`: competition spec JSON
- `deterministic` and `monte-carlo`: trader Python file plus replay CSVs
- diagnostics: official `.log`, sometimes `.json`
- `probe-scaffold`: baseline trader Python file

Spec convention for external data:

- use `observation_channels` when a product depends on a machine-readable feed or keyed observation
- keep `observations` as qualitative notes or backward-compatible free-text hints
- for external-signal products, prefer an explicit plain channel such as:

```json
{
  "observation_channels": [
    {
      "key": "WEATHER_SIGNAL",
      "kind": "plain",
      "role": "signal",
      "description": "External weather feed"
    }
  ]
}
```

- if a legacy config still places structured dicts inside `observations`, TraderFactory will still parse them, but `observation_channels` is the intended clean schema

Spec convention for structural mechanics:

- use `derivative_contract` for option and payoff inputs such as `underlying`, `strike`, `option_kind`, `time_to_expiry_years`, and `volatility`
- use `conversion_rule` for explicit conversion semantics such as `ratio`, `fee`, `delay_steps`, and `lot_size`
- use `auction_rule` for auction scheduling and clearing semantics such as `schedule`, `clearing_rule`, and `prep_window`
- use `basket_definition` for explicit linked-product basket components, divisor, and fair offset
- use `participant_rule` for tracked participants, follow/fade intent, and participant weights
- use `signal_rule` when a product depends on one primary external signal key or signal-latency convention
- keep `custom_fields` as an escape hatch, not the preferred home for standard mechanic inputs

Recommended intake flow:

1. create an intake workspace or render a brief template
2. fill the structured `round_brief.json`
3. run `python3 -m trader_factory.cli brief-to-spec <round_brief.json> --output <spec.json> --report-output <brief_extraction.md>`
4. inspect the extraction report so inferred fields stay explicit
5. run `python3 -m trader_factory.cli validate-spec <spec.json>`
6. fix blocked or high-value validation findings
7. scaffold the project only after the spec is structurally coherent

## Repo Philosophy

The most important rule is:

- organize by capabilities and mechanics
- not by bot version numbers

That means this repo should eventually answer:

- what products exist
- what mechanics they have
- what strategy families match those mechanics
- how to validate the resulting model

It should not become another archive of `Traderv61.py`, `Traderv62.py`, `Traderv63.py` without structure.

## Repository Layout

```text
TraderFactory/
  README.md
  pyproject.toml
  configs/
    examples/
  docs/
  references/
  templates/
    python_trader/
  trader_factory/
    cli.py
    core/
    diagnostics/
    generation/
    optimization/
    probes/
    simulation/
    strategies/
    viewer/
    workflows/
  scripts/
  tests/
```

### `trader_factory/core/`

Holds the universal vocabulary:

- competition specs
- product specs
- mechanic labels
- strategy registry
- mechanic-to-sleeve interpretation and fallback rules

This layer is what lets an agent reason from product mechanics instead of hand-written bot lore.

### `trader_factory/generation/`

Holds the logic that turns a round spec into a baseline build plan.

Right now it produces:

- readable round plans
- spec validation reports
- probe workspaces
- baseline trader projects

Later it should generate stronger sleeve implementations from selected capabilities.

### `trader_factory/strategies/`

Reserved for reusable strategy modules.

This is where strategy families should live by mechanism:

- market making
- directional
- spreads
- options
- baskets
- informed flow
- conversions
- execution

### `trader_factory/simulation/`

Holds the local simulation stack:

- deterministic replay
- headless Monte Carlo robustness
- internal replay utilities

### `trader_factory/optimization/`

Holds:

- CMA-ES
- sweeps
- objective functions
- parameter schemas

### `trader_factory/diagnostics/`

Reserved for:

- official log parsers
- trade quality reports
- dormant-vs-live boundary probes
- passive and aggressive execution probes

### `trader_factory/probes/`

Holds the research-mode execution probe framework:

- probe types and event schemas
- DIAG logging helpers
- research workspace scaffolding

### `trader_factory/workflows/`

Defines the operating modes and playbooks.

This is especially important because your current project already established a useful distinction:

- research mode when the simulator behavior is unclear
- development mode when a validated idea should be turned into a production model

## The Intended End-to-End Workflow

The long-term target workflow is:

1. define the round in a machine-readable spec
2. classify each product by mechanics
3. select strategy families from the registry
4. scaffold a readable baseline trader project
5. run deterministic backtests
6. run Monte Carlo robustness checks
7. run focused optimization
8. if local and official diverge, switch into research mode
9. use probes and diagnostics to learn the execution model
10. if a probe reveals a real edge, switch into development mode
11. build the improved production bot
12. document discoveries and hand off the next step cleanly

That is the exact process this repo is meant to standardize.

## Getting Started Right Now

### 1. Start from a template or example round spec

See:

- [configs/examples/prosperity_round0.json](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/configs/examples/prosperity_round0.json)
- [configs/README.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/configs/README.md)
- [docs/SPEC_INTAKE.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/SPEC_INTAKE.md)

Two practical starting paths now exist:

- copy one of the example specs from `configs/examples/`
- or render a built-in intake template:

```bash
python3 -m trader_factory.cli spec-template generic --output /tmp/new_round_spec.json
python3 -m trader_factory.cli spec-template derivative --output /tmp/new_round_spec.json
```

For raw round-brief intake, the more complete workflow is:

```bash
python3 -m trader_factory.cli intake-workspace generic --output-dir /tmp/new_round_intake
python3 -m trader_factory.cli brief-to-spec /tmp/new_round_intake/round_brief.json --output /tmp/new_round_intake/spec.json --report-output /tmp/new_round_intake/brief_extraction.md
python3 -m trader_factory.cli validate-spec /tmp/new_round_intake/spec.json
```

The bundled examples describe:

- a simple EMERALDS / TOMATOES style round
- a derivative round
- a linked-products round
- a signal and participant round
- a conversion and auction round

They use structured fields such as:

- product
- position limit
- tick size
- price regime
- execution style
- mechanics

That file is only the bundled example. The framework itself is intended to stay product-agnostic and mechanic-driven.

### 2. Validate the spec first

From the `TraderFactory` folder:

```bash
python3 -m trader_factory.cli validate-spec /tmp/new_round_spec.json
```

This catches missing structural inputs before project generation.

If you are starting from a raw brief rather than a finished spec, first run:

```bash
python3 -m trader_factory.cli intake-workspace generic --output-dir /tmp/new_round_intake
python3 -m trader_factory.cli brief-to-spec /tmp/new_round_intake/round_brief.json --output /tmp/new_round_intake/spec.json --report-output /tmp/new_round_intake/brief_extraction.md
```

### 3. Run the planning CLI

From the `TraderFactory` folder:

```bash
python3 -m trader_factory.cli plan /tmp/new_round_spec.json
```

What it does today:

- loads the spec
- recommends strategy capabilities per product
- builds a readable round plan

This is the minimal working seed of the future generator pipeline.

### 4. Run the current engine layer

Deterministic replay:

```bash
python3 -m trader_factory.cli deterministic /absolute/path/to/Trader.py --day -1
python3 -m trader_factory.cli deterministic /absolute/path/to/Trader.py --day -1 --data-root /absolute/path/to/data
```

Official trade quality:

```bash
python3 -m trader_factory.cli official-trade-quality /absolute/path/to/run.log --baseline /absolute/path/to/baseline.log
```

Aggressive markout probe summary:

```bash
python3 -m trader_factory.cli aggressive-markout /absolute/path/to/run.log --json-path /absolute/path/to/run.json
```

Probe workspace scaffold:

```bash
python3 -m trader_factory.cli probe-scaffold aggressive_markout /absolute/path/to/Traderv52.py --context range_buy
```

Project scaffold:

```bash
python3 -m trader_factory.cli scaffold-project configs/examples/prosperity_round0.json --output-dir /tmp/round0_project
```

Monte Carlo:

```bash
python3 -m trader_factory.cli monte-carlo /absolute/path/to/Trader.py
python3 -m trader_factory.cli monte-carlo /absolute/path/to/PrimaryTrader.py --compare-bot /absolute/path/to/BaselineTrader.py
python3 -m trader_factory.cli monte-carlo /absolute/path/to/Trader.py --data-root /absolute/path/to/data
```

Viewer:

```bash
python3 -m trader_factory.cli viewer
python3 -m trader_factory.cli viewer --results-dir /absolute/path/to/extra_results
```

CMA-ES:

```bash
python3 -m trader_factory.cli cmaes configs/examples/v52_tight_cmaes.json
```

Important note:

- the headless Monte Carlo robustness engine is local to TraderFactory
- the Monte Carlo viewer is local to TraderFactory
- deterministic replay and Monte Carlo look in `TraderFactory/data/` first, then fall back to the legacy sibling `Prosperity/Data/` path
- see [docs/ENGINES.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/ENGINES.md)
- detailed Monte Carlo usage is documented in [docs/MONTE_CARLO.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/MONTE_CARLO.md)
- viewer usage is documented in [docs/VIEWER.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/VIEWER.md)
- the CMA-ES engine is local to TraderFactory and documented in [docs/OPTIMIZATION.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/OPTIMIZATION.md)
- the probe framework is local to TraderFactory and documented in [docs/PROBES.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/PROBES.md)
- the baseline project generator is documented in [docs/GENERATION.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/GENERATION.md)

### 5. Read the workflow docs

Start with:

- [docs/WORKFLOW.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/WORKFLOW.md)
- [docs/SPEC_INTAKE.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/SPEC_INTAKE.md)
- [docs/MVP_SCOPE.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/MVP_SCOPE.md)
- [docs/MIGRATION_PLAN.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/MIGRATION_PLAN.md)
- [docs/TRADER_FACTORY_ARCHITECTURE.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/TRADER_FACTORY_ARCHITECTURE.md)
- [docs/OPTIMIZATION.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/OPTIMIZATION.md)
- [docs/MONTE_CARLO.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/MONTE_CARLO.md)
- [docs/VIEWER.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/VIEWER.md)
- [docs/PROBES.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/PROBES.md)
- [docs/GENERATION.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/GENERATION.md)

### 6. Review the source references

The initial scaffold is based on the current project’s real assets.
See:

- [references/SOURCE_MAP.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/references/SOURCE_MAP.md)
- [references/Strategies.txt](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/references/Strategies.txt)
- [references/PUBLIC_STRATEGY_RESEARCH.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/references/PUBLIC_STRATEGY_RESEARCH.md)

## How To Work In This Repo

### If you are starting a new competition round

1. copy an example config from `configs/examples/`
2. or render a template with `spec-template`
3. define the new products and mechanics
4. run `validate-spec`
5. run the planner CLI
6. write or generate the first baseline trader project
7. connect it to deterministic replay
8. connect it to Monte Carlo
9. compare baselines before doing any deep optimization

This is the main operating idea of `TraderFactory`:

- do not start by inventing a complicated bot
- start by classifying mechanics correctly
- choose the smallest sensible baseline
- only then optimize or research

### If you are doing development work

Use development mode when:

- the execution model is sufficiently understood
- the feature is conceptually validated
- you are building or refining a real production improvement

Typical development tasks:

- baseline trader construction
- parameter tuning
- feature additions
- robustness gating
- official result comparison

### If you are doing research work

Use research mode when:

- local and official diverge materially
- a change appears dormant
- passive or aggressive execution behavior is unclear
- a simulator behavior must be learned before strategy changes make sense

Typical research tasks:

- boundary probes
- passive ladder probes
- aggressive markout probes
- official log diagnostics
- discovery logging

### Switching modes

The project should explicitly switch modes instead of blending everything together.

The agreed rule from the current project is:

- stay in research mode while probing uncertainty
- if a probe yields a usable edge, switch into development mode
- build the actual model improvement
- validate it
- then return to research mode if more unknowns remain

That workflow is already formalized in:

- [trader_factory/workflows/modes.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/workflows/modes.py)
- [docs/WORKFLOW.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/WORKFLOW.md)

## How Another Agent Should Continue Work

If another coding agent takes over, it should follow this order:

1. inspect the current round spec or create one
2. read the strategy registry and references
3. generate a baseline plan
4. decide whether the next task is development or research
5. preserve every nontrivial discovery in repo docs, not only in chat

The repo is deliberately being set up so no important process knowledge depends on one conversation thread.

## What Should Eventually Be Migrated Here

The current source repo already contains the raw material.

Highest-priority remaining migrations:

- historical probe bot examples from `Research/execution_probes/`
- richer trader-project generation on top of the current scaffold

The recommended order is documented in:

- [docs/MIGRATION_PLAN.md](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/docs/MIGRATION_PLAN.md)

## What This Repo Must Not Become

Avoid these failure modes:

- another bot graveyard organized only by version numbers
- a giant framework with no real trader output
- an agent-only black box nobody can understand
- a repo that assumes all products look like EMERALDS or TOMATOES
- a repo that only supports the mechanics that happened to matter this round

Another important rule:

- if a capability is only planned and not yet migrated, say so explicitly

This repo should stay honest about what is implemented.

`TraderFactory` should be:

- readable
- modular
- mechanic-driven
- honest about what is implemented
- broad enough to grow into future rounds

## Minimum Success Criterion

This repo is successful if someone new can open it and, with only this repo plus the competition spec, do the following:

1. understand the workflow
2. understand the available strategy families
3. create a structured product/mechanic description
4. scaffold a reasonable baseline approach
5. know which simulators and diagnostics to run
6. know when to switch from development to research and back
7. preserve discoveries for the next agent or teammate

That is the bar this README is trying to set.
