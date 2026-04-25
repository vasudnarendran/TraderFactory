# Round Start Checklist

This document is the operational runbook for a fresh round.

Use it when the round has just opened, the mechanics are still incomplete, and you need a disciplined path from raw brief to first official candidate.

The goal is not to make the agent disappear.
The goal is to keep repetitive work inside TraderFactory and keep judgment-heavy work with the agent.

## Operating Model

TraderFactory should own:

- spec parsing
- spec validation and missing-field reporting
- mechanic vocabulary lookup
- first-pass mechanic-to-sleeve mapping
- project scaffolding
- deterministic replay
- Monte Carlo robustness
- CMA-ES optimization
- official submission automation
- official diagnostics
- probe scaffolding

The agent should own:

- interpreting ambiguous rules from the brief
- deciding which mechanic labels are justified
- designing sleeves for products that are structurally novel
- deciding when evidence is strong enough to promote a change
- deciding when to switch between development mode and research mode

If a mechanic is not clearly recognized, do not guess.
Record it explicitly and keep it visible.

## First Command

Start with an intake workspace, not bot code.

```bash
cd /Users/vasudravinarendran/Documents/Prosperity/TraderFactory

python3 -m trader_factory.cli intake-workspace generic \
  --competition-name Prosperity \
  --round-name round_1 \
  --output-dir ./runs/round_1_intake
```

Profile selection:

- use `generic` if the round is still unclear
- use `derivative` if payoff or expiry structure is obvious
- use `linked` if products are explicitly related
- use `signal_participant` if signals or named traders clearly matter
- use `conversion_auction` if conversion or auction mechanics are explicit

If the wrong profile is chosen initially, that is acceptable.
The intake workspace is meant to be revised as understanding improves.

## Mandatory Intake

These are the minimum fields that should be captured before trusting a generated baseline:

- product symbols
- position limits
- tick sizes
- execution style when known: maker, taker, or mixed
- recognized mechanic labels
- unknown mechanics that cannot yet be mapped confidently
- product-to-product relationships when products are linked
- settlement or payoff rules when payoffs are nonlinear
- any explicit special rules that change pricing or execution

The structured brief now includes:

- `round_opening_checklist`
- `product_opening_checklist`

Work through those first inside `round_brief.json`.
Do not skip them and jump straight to scaffolding.

## Optional But Valuable Intake

- observation channels or external signals
- known participant identities
- hedge ratios
- explicit derivative contracts
- explicit conversion rules
- explicit auction rules
- explicit basket definitions
- explicit participant rules
- explicit signal rules
- scoring quirks
- simulator caveats

Optional information should still be written down when discovered, preferably in `spec.json`. Use typed fields such as `observation_channels`, `basket_definition`, `participant_rule`, `signal_rule`, `derivative_contract`, `conversion_rule`, and `auction_rule` before falling back to `custom_fields`.

## Intake Commands

After editing `raw_brief.md` and `round_brief.json`, regenerate the derived spec:

```bash
python3 -m trader_factory.cli brief-to-spec \
  ./runs/round_1_intake/round_brief.json \
  --output ./runs/round_1_intake/spec.json \
  --report-output ./runs/round_1_intake/brief_extraction.md
```

Then validate:

```bash
python3 -m trader_factory.cli validate-spec \
  ./runs/round_1_intake/spec.json \
  --output ./runs/round_1_intake/validation.md \
  --json-output ./runs/round_1_intake/validation.json
```

Validation rule:

- errors mean blocked
- warnings mean review carefully before generation
- infos are not blockers, but often indicate weak structure or legacy fallback usage

## Classification Rule

Use this decision rule at round start:

1. If a mechanic already fits the current vocabulary, encode it as a recognized mechanic.
2. If the mechanic is real but the vocabulary is not yet expressive enough, record it under `unknown_mechanics`.
3. If the product depends on formulas, relationships, or nonlinear rules, encode those rules explicitly rather than hiding them inside notes.
4. If a mechanic is unclear and would change architecture choice, stop and surface the question to the agent.

## Fallback Modes

TraderFactory uses explicit fallback modes in generated plans and projects:

- `normal`: the known mechanics are sufficient for a first-pass generated sleeve
- `research_overlay`: the trading sleeve can be generated, but execution transfer or simulator behavior should be validated with probes
- `manual_design_required`: the mechanic family is recognized, but the generated project should only provide a safe structural stub
- `manual_review_required`: the mechanics are still too unclear to justify auto-generated trading logic

These modes are not cosmetic.
They are the contract between the fixed program and the agent.

## Generation Checklist

Only generate a baseline project after:

- the spec validates without errors
- the major unknowns are written explicitly
- typed fields are used for structural mechanics where possible
- the round and product checklists are worked through honestly

Once that is true:

```bash
python3 -m trader_factory.cli plan \
  ./runs/round_1_intake/spec.json \
  --output ./runs/round_1_intake/plan.md

python3 -m trader_factory.cli scaffold-project \
  ./runs/round_1_intake/spec.json \
  --output-dir ./projects/round_1_base \
  --name round_1_base
```

## Baseline And Gate Setup

Before consuming official submission slots repeatedly, set a baseline and a local gate policy.

Example:

```bash
python3 -m trader_factory.cli baseline-imc-set \
  --round-id 1 \
  --compare-bot ./projects/round_1_base/trader.py \
  --notes "Initial round 1 baseline"

python3 -m trader_factory.cli gate-imc-set \
  --round-id 1 \
  --deterministic-min-total-delta 0.0 \
  --mc-min-mean-delta 0.0 \
  --mc-min-plausible-mean-delta 0.0 \
  --notes "Require non-negative local deltas before official submission"
```

These thresholds are examples, not universal truths.
Tighten them once you understand the round better.

## Local Development Pass

Do not start with immediate official submissions.
Run the local gate first:

```bash
python3 -m trader_factory.cli develop-cycle-imc \
  ./projects/round_1_base/trader.py \
  --round-id 1 \
  --dry-run
```

If you want direct access to the lower-level tools:

```bash
python3 -m trader_factory.cli deterministic \
  ./projects/round_1_base/trader.py \
  --day -1 \
  --output ./runs/deterministic_round_1

python3 -m trader_factory.cli monte-carlo \
  ./projects/round_1_base/trader.py \
  --quick \
  --output-dir ./runs/mc_round_1
```

## Official Development Pass

Only move to official submission when:

- the spec is structurally coherent
- the current baseline trader is understandable
- local deterministic behavior is sane
- Monte Carlo results do not immediately reject the candidate

Primary official command:

```bash
python3 -m trader_factory.cli develop-cycle-imc \
  ./projects/round_1_base/trader.py \
  --round-id 1
```

If you want only the queue-aware official automation without the local gate wrapper:

```bash
python3 -m trader_factory.cli official-cycle-imc \
  ./projects/round_1_base/trader.py \
  --round-id 1
```

## Research Trigger

Switch to research mode if any of the following happens:

- local replay and official behavior disagree materially
- a feature appears dormant officially
- execution quality changes without a structural explanation
- simulator mechanics are still unclear enough that optimization would be noise

When that happens, stop patching the production candidate and diagnose the boundary.

Useful commands:

```bash
python3 -m trader_factory.cli official-trade-quality \
  /path/to/result.log \
  --primary-json /path/to/result.json \
  --baseline /path/to/baseline.log \
  --baseline-json /path/to/baseline.json \
  --output-dir ./runs/official_analysis

python3 -m trader_factory.cli boundary-probe \
  /path/to/result.log \
  --output-dir ./runs/official_analysis

python3 -m trader_factory.cli passive-ladder \
  /path/to/result.log \
  --json-path /path/to/result.json \
  --output-dir ./runs/official_analysis

python3 -m trader_factory.cli aggressive-markout \
  /path/to/result.log \
  --json-path /path/to/result.json \
  --output-dir ./runs/official_analysis
```

If a dedicated probe bot is needed:

```bash
python3 -m trader_factory.cli probe-scaffold \
  boundary \
  ./projects/round_1_base/trader.py \
  --product PRODUCT_A \
  --output-dir ./runs/probes
```

## Optimization Rule

Do not optimize a product aggressively until:

- its fallback mode is understood
- its intake gaps are recorded
- deterministic replay is stable
- the generated sleeve is appropriate for the actual mechanics

If a product is in `manual_review_required`, intake comes before optimization.

If a product is in `manual_design_required`, architecture comes before optimization.

If a product is in `research_overlay`, development and probe work should stay separate.

When the round is ready for optimization, use CMA-ES only after the structure and transfer story are reasonably stable:

```bash
python3 -m trader_factory.cli cmaes \
  /path/to/optimization_config.json \
  --output-dir ./runs/cmaes_round_1
```

Inspect results with:

```bash
python3 -m trader_factory.cli viewer --results-dir ./runs
```

## Round-Start Workflow Summary

1. Create an intake workspace.
2. Fill `raw_brief.md` and `round_brief.json`.
3. Work through `round_opening_checklist` and each `product_opening_checklist`.
4. Regenerate `spec.json` with `brief-to-spec`.
5. Run `validate-spec`.
6. Fix blocked structural issues.
7. Generate `plan.md` and scaffold the baseline trader project.
8. Set baseline and gate policy for the round.
9. Run `develop-cycle-imc --dry-run`.
10. Submit officially only when local gates are acceptable.
11. If transfer disagrees, stop optimizing and move into diagnostics or probes.
12. Return to development mode only after the research question is narrowed enough to act on.

## Decision Rule

Use this quick rule:

- if the structure is unclear, stay in intake
- if the structure is clear but transfer is unclear, stay in research
- if the structure and transfer are both good enough, move into development
- if development fails officially, go back to research with explicit probes

## Why This Matters

The biggest failure mode is not missing a fancy strategy.
It is letting the repo or the agent pretend a product is understood when it is not.

TraderFactory should compress mechanical work.
It should not compress uncertainty out of existence.
