# Generation

`TraderFactory` can now scaffold a capability-aware baseline trader project from a competition spec.

Entry point:

- [trader_factory/generation/project.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/generation/project.py)

CLI:

```bash
python3 -m trader_factory.cli spec-template generic --output /tmp/new_round_spec.json
python3 -m trader_factory.cli brief-template generic --output /tmp/new_round_brief.json
python3 -m trader_factory.cli intake-workspace generic --output-dir /tmp/new_round_intake
python3 -m trader_factory.cli brief-to-spec /tmp/new_round_intake/round_brief.json --output /tmp/new_round_intake/spec.json --report-output /tmp/new_round_intake/brief_extraction.md
python3 -m trader_factory.cli validate-spec /tmp/new_round_spec.json
python3 -m trader_factory.cli scaffold-project /tmp/new_round_spec.json
```

Legacy bundled example:

```bash
python3 -m trader_factory.cli scaffold-project configs/examples/prosperity_round0.json
```

Explicit output directory:

```bash
python3 -m trader_factory.cli scaffold-project \
  configs/examples/prosperity_round0.json \
  --output-dir /tmp/prosperity_round0_project \
  --name round0_baseline
```

## What It Generates

- `README.md`
- `spec.json`
- `spec_validation.md`
- `spec_validation.json`
- `plan.md`
- `params.py`
- `trader.py`
- `notes.md`
- `round_start_checklist.md`
- `experiments/README.md`
- `experiments/cmaes_template_<product>.json`
- `research/README.md`
- `research/probe_targets.md`
- `research/structural_design_brief.md`

## Design Goal

This is a baseline project scaffold, not a full auto-trader generator.

It is meant to:

- render reusable intake templates for common mechanic profiles
- copy the structured round spec
- surface explicit validation findings before development starts
- preserve the generated round plan
- create a readable multi-product baseline trader with archetype-aware sleeves
- create experiment templates so the project can immediately enter replay, Monte Carlo, and optimization
- create research notes so execution probes are not an afterthought
- keep the next development step concrete

It is not meant to:

- invent a final strategy automatically
- replace deliberate model design
- hide product logic inside a giant framework

## Current Scope

What is implemented:

- built-in intake-template profiles via `spec-template`
- project directory scaffolding
- spec validation with machine-readable and human-readable findings
- per-product archetype selection
- structured `observation_channels` support for machine-readable external inputs in the intake spec
- structured `derivative_contract`, `conversion_rule`, and `auction_rule` support for common structural mechanics
- structured `basket_definition`, `participant_rule`, and `signal_rule` support for linked, participant, and signal-driven products
- runnable baseline sleeves for anchored, simple market-making, and directional microstructure products
- runnable residual-aware sleeve for simple two-leg linked products
- runnable weighted-basket sleeve when explicit components are declared
- runnable vanilla-option sleeve when explicit pricing inputs are declared
- runnable conversion-observation sleeve for simple conversion products
- runnable participant-flow sleeve when tracked participants are declared explicitly
- runnable external-signal sleeve when the signal source is declared explicitly
- blueprint-driven deliberate stubs for spread, derivative, participant, conversion, auction, storage, external-signal, and unresolved products
- copied spec and plan
- baseline parameter and metadata file
- experiment template generation
- research template generation
- explicit fallback modes, intake gaps, and round-start checklists

Validation behavior:

- flags invalid base fields such as nonpositive position limits or tick sizes
- flags missing structural inputs for basket, derivative, conversion, auction, participant, and signal-driven products
- flags unresolved unknown mechanics and open questions
- flags structural inputs that still live in `custom_fields` instead of typed schema blocks
- writes `spec_validation.md` and `spec_validation.json` into every generated project

Input convention:

- use `spec-template` or one of the bundled examples when starting a new round intake
- use `observation_channels` for actual replay-visible feeds such as plain signals or future keyed observations
- use `derivative_contract`, `conversion_rule`, and `auction_rule` for standard structural mechanics before reaching for `custom_fields`
- use `basket_definition`, `participant_rule`, and `signal_rule` for linked baskets, participant semantics, and explicit signal-source selection before reaching for `custom_fields`
- keep `observations` as qualitative notes when you only want to preserve human context

What is still missing:

- automatic sleeve code generation from capability sets
- richer runnable sleeves for broader baskets, richer derivatives, richer participant-flow, richer external-signal, richer conversion, and auction products
- generated official-submission packaging from each project
