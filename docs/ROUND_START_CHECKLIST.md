# Round Start Checklist

This document defines how TraderFactory should be used when a new round opens and the mechanics are only partially known.

The goal is not to make the agent disappear.
The goal is to remove repetitive token-heavy work from the agent and leave only the parts that require judgment.

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

## Classification Rule

Use this decision rule at round start:

1. If a mechanic already fits the current vocabulary, encode it as a recognized mechanic.
2. If the mechanic is real but the vocabulary is not yet expressive enough, record it under `unknown_mechanics`.
3. If the product depends on formulas, relationships, or nonlinear rules, encode those rules explicitly rather than hiding them inside notes.
4. If a mechanic is unclear and would change architecture choice, stop and surface the question to the agent.

## Fallback Modes

TraderFactory now uses explicit fallback modes in generated plans and projects:

- `normal`: the known mechanics are sufficient for a first-pass generated sleeve
- `research_overlay`: the trading sleeve can be generated, but execution transfer or simulator behavior should be validated with probes
- `manual_design_required`: the mechanic family is recognized, but the generated project should only provide a safe structural stub
- `manual_review_required`: the mechanics are still too unclear to justify auto-generated trading logic

These modes are not cosmetic.
They are the contract between the fixed program and the agent.

## Promotion Rule

Do not optimize a product aggressively until:

- its fallback mode is understood
- its intake gaps are recorded
- deterministic replay is stable
- the generated sleeve is appropriate for the actual mechanics

If a product is in `manual_review_required`, intake comes before optimization.

If a product is in `manual_design_required`, architecture comes before optimization.

If a product is in `research_overlay`, development and probe work should stay separate.

## Round-Start Workflow

1. Start from `spec-template` or a bundled example and capture the new round in a spec JSON.
2. Keep recognized and unknown mechanics separate.
3. Run `python3 -m trader_factory.cli validate-spec <spec.json>`.
4. Fix blocked findings and review the warnings that matter structurally.
5. Run `plan` or `scaffold-project`.
6. Inspect fallback modes, intake gaps, validation findings, and research triggers.
7. Resolve structural unknowns first.
8. Only then move to development mode for replay, optimization, and official submission.

## Why This Matters

The biggest failure mode is not missing a fancy strategy.
It is letting the repo or the agent pretend a product is understood when it is not.

TraderFactory should compress mechanical work.
It should not compress uncertainty out of existence.
