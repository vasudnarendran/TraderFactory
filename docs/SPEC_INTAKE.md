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
2. If the round brief is still raw, create an intake workspace or render a `brief-template`.
3. Replace placeholder product names, limits, and mechanics with actual round facts.
4. Use typed fields for structural mechanics whenever possible.
5. Keep unresolved uncertainty in `unknown_mechanics`, `open_questions`, or `special_rules`.
6. Convert the structured brief into a spec with `brief-to-spec` if needed.
7. Run `validate-spec`.
8. Fix blocked findings.
9. Scaffold the project only after the spec is structurally coherent.

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

## Structured Brief Workflow

When the round first opens, you often do not have a clean spec yet. You have copied rules text, notes, screenshots, and partial facts.

For that case, TraderFactory now includes:

```bash
python3 -m trader_factory.cli brief-template generic
python3 -m trader_factory.cli intake-workspace generic --output-dir /tmp/new_round_intake
python3 -m trader_factory.cli brief-to-spec /tmp/new_round_intake/round_brief.json --output /tmp/new_round_intake/spec.json --report-output /tmp/new_round_intake/brief_extraction.md
```

The intended meaning:

- `brief-template`: render a structured `round_brief.json` shape directly
- `intake-workspace`: create a full folder with `raw_brief.md`, `round_brief.json`, derived `spec.json`, and `brief_extraction.md`
- `brief-to-spec`: regenerate the spec after you edit the structured brief, plus an extraction report if requested

This is the recommended bridge from raw brief text to validated machine-readable spec.

The structured brief now also carries an explicit checklist layer:

- `round_opening_checklist`: machine-readable round-level intake tasks with `required_now` and `nice_to_have` sections
- `product_opening_checklist`: per-product intake tasks attached to each product entry

Each checklist item includes:

- `id`
- `prompt`
- `why_it_matters`
- `target_fields`
- `sources_to_check`
- `status`
- `evidence`
- `notes`

The intent is to move the highest-value round-opening questions into the JSON itself so a human or agent can work the intake systematically instead of relying on scattered docs.

## Helper Hints

The structured brief now includes helper fields that sit between raw prose and fully typed schema blocks.

Useful product-level helpers:

- `underlying_hint`
- `related_products_hint`
- `relationship_style_hint`
- `target_product_hint`
- `source_product_hint`
- `signal_source_hint`
- `raw_brief_excerpt`
- `source_notes`

The checklist layer and the helper-hint layer serve different purposes:

- checklists tell you what to collect next
- helper hints give `brief-to-spec` a conservative bridge from prose into typed fields

These fields do not replace typed schema blocks. They exist so `brief-to-spec` can conservatively fill obvious missing structure without making the agent hand-author every nested JSON field immediately.

Current inference rules are intentionally conservative:

- typed schema always wins over hints
- hints win over free-text inference
- free-text inference is limited to obvious mechanic, regime, execution-style, and single-reference cases
- all inferred fields are recorded in `brief_extraction.md`

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

1. raw brief capture
2. structured brief intake
3. spec extraction
4. validation
5. scaffolding
6. deterministic replay
7. Monte Carlo
8. optimization
9. official submission
10. diagnostics or probes if transfer disagrees
