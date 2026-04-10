# TraderFactory Architecture

This document defines a grounded architecture for a new repo called `TraderFactory`.

It is based on the material that already exists in:

- `Prosperity`
- `MyProsperity`

The goal is not to invent a generic quant platform from scratch.
The goal is to extract the parts of the current workflow that are already real, useful, and reusable:

- strategy development
- bot scaffolding
- local backtesting
- Monte Carlo robustness testing
- parameter optimization
- official-log analysis
- execution probes
- research documentation
- agent handoff workflow

## 1. Goal

`TraderFactory` should be a mechanic-driven bot development system.

The user should be able to provide:

- a set of products
- product mechanics
- position limits
- market conventions
- optional product relationships
- optional special rules such as conversion, options, baskets, or informed traders

and then use the repo plus an agent to:

1. select relevant strategy families
2. scaffold a bot architecture
3. generate baseline traders
4. run local backtests
5. run Monte Carlo robustness checks
6. optimize parameters
7. analyze failures and official logs
8. run targeted probes when the simulator behavior is unclear
9. document discoveries
10. produce a submission-ready trader

## 2. What Already Exists And Should Be Reused

This design is grounded in the current repos rather than imagined tooling.

### 2.1 Trading bots and model line

Current reusable material:

- `Prosperity/Bots/`
- `MyProsperity/Bots/`
- `Prosperity/Bots/datamodel.py`
- `MyProsperity/Bots/datamodel.py`

Important validated bot references:

- `Traderv37.py`: historical strong official baseline
- `Traderv51.py`: clean faithful reconstruction
- `Traderv52.py`: current best clean official result in the current line

What this contributes to `TraderFactory`:

- bot interface contract
- multi-product trader layout
- product-specific trader sleeves
- persistent `traderData` pattern
- practical examples of signal, execution, and inventory logic

### 2.2 Local deterministic backtesting

Current reusable material:

- `Backtest_failed_Python/run_backtest.py`
- `Backtest_failed_Python/README.md`

What this contributes:

- direct loading of bot files
- replay from CSV market snapshots
- deterministic single-path simulation
- per-step and per-product logs
- plotting and summary output

Important limitation to preserve in the new design:

- this is a useful local approximation, not the hidden official simulator

So in `TraderFactory`, deterministic replay should be a first-class tool, but never the only validation layer.

### 2.3 Monte Carlo robustness stack

Current reusable material:

- `MonteCarloBacktester/prosperity4mcbt/`
- `MonteCarloBacktester/prosperity3bt/`
- `MonteCarloBacktester/monte_carlo_viewer/`
- `Analysis/v52_monte_carlo_robustness.py`
- `Analysis/monte_carlo_sensitivity_report.py`
- `MONTE_CARLO_COMPARISON.md`

What this contributes:

- a session-based Monte Carlo engine
- dashboard generation and viewing
- robustness gating beyond nominal local PnL
- sensitivity analysis by fill and slippage assumptions

Important design lesson from current work:

- Monte Carlo is valuable as an evaluation and robustness tool
- it is not itself a source of alpha

### 2.4 Parameter search and optimization

Current reusable material:

- `Analysis/v31_cmaes_optimize.py`
- `Analysis/v33_cmaes_optimize.py`
- `Analysis/v51_cmaes_optimize.py`
- `Analysis/v52_cmaes_optimize.py`
- `Analysis/v53_memory_cmaes_optimize.py`
- `Analysis/v37_feature_sweep.py`
- `Analysis/focused_bot_cmaes.py`

What this contributes:

- CMA-ES workflow
- candidate patching / parameter injection pattern
- evaluation objective design
- constrained local search around a validated baseline

Important design lesson:

- optimization is most useful after structural logic is trusted
- optimizing dormant or weakly-live logic wastes time

### 2.5 Official log analysis and execution probes

Current reusable material:

- `Analysis/official_trade_quality_report.py`
- `Analysis/official_diag_report.py`
- `Analysis/official_boundary_probe_report.py`
- `Analysis/official_passive_ladder_report.py`
- `Analysis/official_aggressive_markout_probe_report.py`
- `Research/execution_probes/`

What this contributes:

- fill-level official log postmortems
- boundary probing for dormant-vs-live logic
- passive ladder probing
- aggressive markout probing
- a repeatable research workflow for hidden-simulator discovery

Important design lesson:

- when local and official diverge, the correct response is often research tooling, not more strategy code

### 2.6 Strategy and research documentation

Current reusable material:

- `Strategies.txt`
- `PUBLIC_STRATEGY_RESEARCH.md`
- `MyProsperity/model_handoff_for_codex.md`
- `Research/execution_probes/DISCOVERIES.md`
- `Research/execution_probes/RESEARCH_HANDOFF.md`
- `Research/execution_probes/docs/`

What this contributes:

- reusable strategy taxonomy
- grounded ideas from public competition writeups
- handoff conventions for agents
- canonical discovery log structure

Important design lesson:

- research should not live only in chat history
- every reusable discovery needs a durable home

## 3. Core Design Principle

`TraderFactory` should be organized by capabilities, not by bot versions.

That means:

- not `Traderv61.py`, `Traderv62.py`, `Traderv63.py` as the main organizing principle
- instead:
  - market spec
  - strategy families
  - simulation engines
  - optimization workflows
  - research workflows
  - generated project outputs

Versioned trader files should still exist, but as outputs of the factory process, not as the repo architecture itself.

## 4. Recommended Repo Structure

```text
TraderFactory/
  README.md
  pyproject.toml
  trader_factory/
    core/
      datamodel/
      specs/
      templates/
      registry/
    strategies/
      market_making/
      directional/
      spreads/
      options/
      baskets/
      informed_flow/
      conversions/
      execution/
    generation/
      scaffolding/
      composition/
      parameter_maps/
    simulation/
      deterministic/
      monte_carlo/
      adapters/
    optimization/
      cmaes/
      sweeps/
      objectives/
    diagnostics/
      official_logs/
      trade_quality/
      probes/
      dashboards/
    workflows/
      develop/
      research/
      handoff/
    docs/
      strategy_library/
      mechanics_library/
      playbooks/
  configs/
    products/
    competitions/
    experiments/
  generated/
    projects/
    reports/
    runs/
  scripts/
  tests/
```

## 5. What Each Layer Should Do

### 5.1 `core/`

Purpose:

- define the universal vocabulary of the system

Should contain:

- canonical trading datamodel interfaces
- product specification schema
- mechanic specification schema
- capability registry
- code templates for generated trader projects

Key objects that should exist:

- `CompetitionSpec`
- `ProductSpec`
- `MechanicSpec`
- `BotArchitectureSpec`
- `ExperimentSpec`
- `StrategyCapability`

This layer should answer:

- what is being traded
- what rules apply
- what classes of strategy are even relevant

### 5.2 `strategies/`

Purpose:

- hold reusable strategy modules by mechanism, not by competition round

Subfolders should be capability-oriented.

Examples:

- `market_making/`
  - static fair maker
  - join/improve maker
  - inventory-skew maker
  - AS/GLFT-style quote controller
- `directional/`
  - mean reversion
  - trend following
  - breakout
  - residual-based reversion
- `spreads/`
  - pair spreads
  - basket residuals
  - offset trades
- `options/`
  - parity checks
  - implied-vol approximation
  - delta-aware hedging sleeves
- `informed_flow/`
  - informed-agent tracking
  - copy / fade logic
- `execution/`
  - passive go/no-go
  - take-vs-wait decision
  - inventory relief
  - participation control

This is where previously irrelevant strategies should live too.
Even if options or conversions were not useful for EMERALDS/TOMATOES, they belong in `TraderFactory` because future rounds may need them.

### 5.3 `generation/`

Purpose:

- turn specs plus strategy choices into runnable trader code

This layer should:

- select a bot skeleton from the mechanics
- compose product sleeves
- instantiate parameter maps
- generate a clean trader project directory
- keep generated code readable

Key requirement:

- generated bots should be understandable Python files, not opaque machine-produced blobs

Suggested output:

- a generated trader project with:
  - `Trader.py`
  - `products/`
  - `params.py`
  - `README.md`
  - `experiments/`

### 5.4 `simulation/`

Purpose:

- provide all local validation engines behind a consistent interface

Subcomponents:

- `deterministic/`
  - adapted from `run_backtest.py`
- `monte_carlo/`
  - adapted from `prosperity4mcbt`
- `adapters/`
  - competition-specific data loaders
  - log readers
  - output normalizers

Key interface idea:

- the agent should not need to remember different CLI details for each simulator
- it should call one standard experiment interface

Example conceptual API:

- `run_deterministic(spec, trader_path, dataset, output_dir)`
- `run_monte_carlo(spec, trader_path, profile, output_dir)`

### 5.5 `optimization/`

Purpose:

- separate optimization logic from strategy code

Subcomponents:

- `cmaes/`
- `sweeps/`
- `objectives/`

Important requirement:

- objectives should be configurable by phase

Examples:

- development objective:
  - maximize mean nominal replay
- robust objective:
  - maximize mean with downside penalty
- transfer objective:
  - maximize mean while penalizing drift and one-day collapse

Optimization should consume:

- parameter schema
- candidate generator
- evaluation runner
- comparison baseline

### 5.6 `diagnostics/`

Purpose:

- explain why a bot behaved the way it did

Subcomponents:

- `official_logs/`
  - parsers for official logs and json
- `trade_quality/`
  - fill-level edge and markout reports
- `probes/`
  - boundary, passive, aggressive, and future probe families
- `dashboards/`
  - dashboard server and schema adapters

This layer is critical.

The current project already showed that large improvements often require better diagnostics, not new indicators.

### 5.7 `workflows/`

Purpose:

- encode the development and research process itself

Recommended workflow packages:

- `develop/`
  - build a candidate model from known ideas
- `research/`
  - probe unknown simulator or execution behavior
- `handoff/`
  - summarize findings and next steps for another agent

This should formalize the working rule already established in your current project:

- stay in research mode while probing unknown mechanics
- if a probe yields a usable edge, switch to development mode
- implement the model improvement
- validate it
- then return to research mode if uncertainty remains

## 6. Core Input Model: Product And Mechanic Specs

This is the single most important design decision.

`TraderFactory` should start from structured specs, not from handwritten bot ideas.

### 6.1 `ProductSpec`

Each product spec should capture at least:

- symbol
- position limit
- tick size
- likely price regime
  - anchored
  - drifting
  - seasonal
  - latent-fair
  - spread-linked
- observed book behavior
  - tight/stable
  - thin/noisy
  - wall-driven
  - informed-flow-sensitive
- execution importance
  - mostly passive
  - mixed
  - mostly aggressive

### 6.2 `MechanicSpec`

Each mechanic spec should capture features such as:

- static anchor
- latent fair
- order-book imbalance relevance
- mean reversion tendency
- breakout tendency
- informed trader presence
- option-like payoff
- conversion path
- basket linkage
- external state / observations
- discrete event triggers

These specs should drive:

- which strategy families are suggested
- which simulators are required
- which diagnostics matter
- which probes are relevant

### 6.3 Example of the intended flow

Input:

- product A: anchored maker product
- product B: short-horizon directional microstructure product
- product C: option on product B

Factory output:

- A gets static fair + join/improve + inventory skew
- B gets predictive fair + regime control + execution controller
- C gets option parity / hedge-aware sleeve
- optimizer chooses separate parameter maps
- diagnostics recommend option-specific Greeks/parity reports and B-execution probes

## 7. Strategy Registry

`TraderFactory` should not hardwire all logic into one big agent prompt.

It should have a registry of strategies with explicit metadata.

Each strategy module should declare:

- name
- description
- applicable mechanics
- incompatible mechanics
- required inputs
- produced outputs
- typical risks
- whether it changes:
  - fair value
  - target position
  - quote policy
  - taker policy
  - hedge policy

Example:

- `static_anchor_mm`
  - applicable to anchored products
  - requires best bid/ask and inventory
  - outputs fair, quotes, and passive size bias

- `short_horizon_regression_alpha`
  - applicable to drifting or directional products
  - requires history window
  - outputs predicted edge and fit quality

- `option_parity_checker`
  - applicable to derivative products
  - requires underlying fair and option strike/expiry
  - outputs theoretical value gap and hedge suggestion

This registry is what lets an agent assemble a bot systematically.

## 8. Recommended Agent Workflow

The agent workflow should be explicit and repeatable.

### Phase A: Intake

Read:

- competition rules
- products
- mechanics
- data availability
- position limits

Write:

- `CompetitionSpec`
- `ProductSpec`s
- first-pass mechanic labels

### Phase B: Strategy selection

Use the registry to choose:

- base strategy per product
- secondary overlays
- what not to use

Write:

- strategy rationale
- rejected strategy rationale

### Phase C: Bot generation

Generate:

- baseline trader project
- parameter schema
- experiment config

### Phase D: Development validation

Run:

- deterministic backtests
- Monte Carlo robustness
- focused sweeps / CMA-ES if the logic is already trusted

### Phase E: Research mode

If local-vs-official mismatch appears:

- switch to probe workflow
- use diagnostics and official-log analysis
- update discovery log

### Phase F: Development mode

If research reveals a real edge:

- build the feature into the production bot
- rerun development validation
- compare against baseline

### Phase G: Handoff

Persist:

- discoveries
- decisions
- current baseline
- next recommended experiments

## 9. MVP Scope

Do not try to build the entire lifetime platform in version 1.

### 9.1 What the MVP should include

The first `TraderFactory` MVP should focus on the capabilities you already know are real:

- product/mechanic spec schema
- deterministic replay adapter
- Monte Carlo adapter
- CMA-ES runner
- official-log analysis
- probe framework
- strategy registry for:
  - anchored market making
  - directional microstructure trading
  - inventory relief
  - simple residual / spread trading
- agent handoff/documentation conventions

### 9.2 What should wait until later

These should be represented in the architecture, but not necessarily implemented first:

- options engine
- basket hedging engine
- conversion mechanics
- online learner framework
- portfolio optimization across many products
- automatic codegen for every possible mechanic

The MVP should be honest about what it can already do well.

## 10. Migration Plan From Current Repos

### Stage 1: Create the repo and preserve knowledge

Copy in first:

- `Strategies.txt`
- `PUBLIC_STRATEGY_RESEARCH.md`
- `Research/execution_probes/`
- Monte Carlo viewer and runner
- deterministic backtester
- key bot references:
  - `Traderv37.py`
  - `Traderv51.py`
  - `Traderv52.py`

This gives the repo real value immediately.

### Stage 2: Extract reusable tools

Refactor into reusable packages:

- deterministic simulator wrapper
- Monte Carlo wrapper
- CMA-ES wrapper
- official log analyzers
- probe analyzers

### Stage 3: Create spec-driven scaffolding

Add:

- `ProductSpec`
- `MechanicSpec`
- baseline strategy registry
- trader project generator

### Stage 4: Add workflow automation

Implement agent playbooks for:

- `new_round_bootstrap`
- `new_product_bootstrap`
- `candidate_optimize`
- `candidate_probe`
- `official_postmortem`

### Stage 5: Add richer mechanic families

Only after the core system works:

- options
- baskets
- conversions
- informed-flow modules

## 11. Recommended Source Mapping

This is the cleanest migration map from the current repos.

### Move almost directly

- `Prosperity/MonteCarloBacktester/prosperity4mcbt/`
- `Prosperity/MonteCarloBacktester/monte_carlo_viewer/`
- `Prosperity/Analysis/official_trade_quality_report.py`
- `Prosperity/Analysis/official_boundary_probe_report.py`
- `Prosperity/Analysis/official_passive_ladder_report.py`
- `Prosperity/Analysis/official_aggressive_markout_probe_report.py`
- `Prosperity/Analysis/v51_cmaes_optimize.py`
- `Prosperity/Analysis/v52_cmaes_optimize.py`
- `Prosperity/Research/execution_probes/`
- `Prosperity/PUBLIC_STRATEGY_RESEARCH.md`
- `Prosperity/Strategies.txt`

### Refactor before copying

- `Backtest_failed_Python/run_backtest.py`
  - useful, but should become a reusable simulation package
- `Bots/datamodel.py`
  - good base, but should become a core shared datamodel module
- bot files
  - should become templates / references / generated outputs, not the repo architecture

### Keep as reference only

- archived bot history
- one-off sweep scripts tied tightly to specific bot versions

Those are useful for research history, but they should not define the `TraderFactory` code structure.

## 12. What Success Looks Like

`TraderFactory` is successful if, for a new round, you can do this:

1. write a competition spec and product/mechanic specs
2. ask the agent to bootstrap a round
3. get a readable baseline trader project
4. run deterministic and Monte Carlo evaluation from one interface
5. run focused optimization from a parameter schema
6. run official postmortems and probes when the local model is insufficient
7. preserve discoveries in durable docs
8. promote a validated candidate into the active competition repo

If that works, then the repo is doing what you want:

- not replacing research
- not replacing judgment
- but making the whole round-to-round process faster, cleaner, and more systematic

## 13. Recommendation

Build `TraderFactory` in two tracks:

### Track 1: Tooling extraction

Create a real reusable toolkit from:

- simulators
- Monte Carlo
- optimizers
- analyzers
- probe framework
- documentation workflow

### Track 2: Spec-driven generation

Build the product/mechanic registry and baseline scaffolding layer.

Do not start by trying to auto-build the perfect trader.
Start by making the repo capable of generating a sound baseline and then driving the same analysis loop you already know works.

That is the highest-confidence path.
