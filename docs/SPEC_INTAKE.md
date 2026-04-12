# Spec Intake

This document defines the practical intake workflow for a new round.

The goal is not to describe the round perfectly on the first pass.
The goal is to capture the round in a machine-readable form that is explicit about what is known, what is unknown, and what still blocks safe generation.

## Working Rule

Do not start with bot code.

Start with a spec that is good enough to:

- classify products into mechanic families
- surface structural unknowns explicitly
- run `validate-spec`
- scaffold a baseline project without hiding missing assumptions

## Intake Workflow

1. Pick the closest built-in template profile.
2. Replace placeholder product names, limits, and mechanics with actual round facts.
3. Use typed fields for structural mechanics whenever possible.
4. Keep unresolved uncertainty in `unknown_mechanics`, `open_questions`, or `special_rules`.
5. Run `validate-spec`.
6. Fix blocked findings.
7. Scaffold the project only after the spec is structurally coherent.

## Built-In Template Profiles

TraderFactory now includes a `spec-template` CLI:

```bash
python3 -m trader_factory.cli spec-template generic
python3 -m trader_factory.cli spec-template derivative
python3 -m trader_factory.cli spec-template linked
python3 -m trader_factory.cli spec-template signal_participant
python3 -m trader_factory.cli spec-template conversion_auction
```

Profile guidance:

- `generic`: use when the round is still mostly unknown and you only need a safe shell to start filling in.
- `derivative`: use when one or more products have explicit underlying, strike, expiry, or payoff structure.
- `linked`: use when product fair depends on other traded products or explicit basket composition.
- `signal_participant`: use when external observations or named participants materially affect fair value or aggression.
- `conversion_auction`: use when products convert across states or venues, or when timing is dominated by auction windows.

## Bundled Example Specs

Use these as concrete references:

- [configs/examples/prosperity_round0.json](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/configs/examples/prosperity_round0.json)
- [configs/examples/future_derivative_round.json](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/configs/examples/future_derivative_round.json)
- [configs/examples/future_linked_round.json](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/configs/examples/future_linked_round.json)
- [configs/examples/future_signal_participant_round.json](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/configs/examples/future_signal_participant_round.json)
- [configs/examples/future_conversion_auction_round.json](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/configs/examples/future_conversion_auction_round.json)

## Information To Research At Round Start

These facts are the highest-value inputs to gather early:

- exact product symbols
- exact position limits
- exact tick sizes
- whether the product is maker-like, taker-like, or mixed
- whether fair is stable, drifting, linked, nonlinear, or signal-driven
- whether products are linked by explicit weights, spreads, or transformations
- whether any product has option-style payoff, expiry, or special settlement
- whether any product has conversion ratio, fee, delay, or transport semantics
- whether any product clears through an auction or time-windowed process
- whether there are replay-visible external observations
- whether participant identity matters and how it appears in the feed

## Typed Field Rule

When a standard structural concept exists, use the typed field first:

- `observation_channels`
- `basket_definition`
- `participant_rule`
- `signal_rule`
- `derivative_contract`
- `conversion_rule`
- `auction_rule`

Use `custom_fields` only when:

- the current schema is genuinely missing a concept
- you need to preserve a round-specific fact before the schema is extended

## Validation Rule

Run this before `plan` or `scaffold-project`:

```bash
python3 -m trader_factory.cli validate-spec /path/to/spec.json
```

Interpretation:

- errors: blocked; fix before generation
- warnings: review carefully; they usually indicate unresolved structure or ambiguity
- infos: not blockers, but often indicate legacy-field reliance or special handling worth cleaning up

## Promotion Rule

If the spec is weak, optimization quality is meaningless.

So the order remains:

1. intake
2. validation
3. scaffolding
4. deterministic replay
5. Monte Carlo
6. optimization
7. official submission
8. diagnostics or probes if transfer disagrees
