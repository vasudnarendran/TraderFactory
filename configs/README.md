# Configs

This directory holds reusable machine-readable inputs for TraderFactory workflows.

## Layout

- `examples/`: validated example specs and optimization configs
- `baselines/`: local baseline-policy files used by recurring workflows

## Round Intake

For a new competition round, start from one of two paths:

1. Render a built-in intake template:

```bash
python3 -m trader_factory.cli spec-template generic --output /tmp/new_round_spec.json
python3 -m trader_factory.cli spec-template derivative --output /tmp/new_round_spec.json
python3 -m trader_factory.cli spec-template linked --output /tmp/new_round_spec.json
python3 -m trader_factory.cli spec-template signal_participant --output /tmp/new_round_spec.json
python3 -m trader_factory.cli spec-template conversion_auction --output /tmp/new_round_spec.json
```

2. Copy and adapt an example from `examples/`:

- `prosperity_round0.json`
- `future_derivative_round.json`
- `future_linked_round.json`
- `future_signal_participant_round.json`
- `future_conversion_auction_round.json`

After editing the spec, validate it before scaffolding:

```bash
python3 -m trader_factory.cli validate-spec /tmp/new_round_spec.json
```

Then scaffold the project:

```bash
python3 -m trader_factory.cli scaffold-project /tmp/new_round_spec.json --output-dir /tmp/new_round_project
```

## Design Rule

Keep `custom_fields` as an escape hatch.
When the repo already has typed fields such as `observation_channels`, `basket_definition`, `participant_rule`, `signal_rule`, `derivative_contract`, `conversion_rule`, or `auction_rule`, use those first.

## Raw Brief Workflow

If you are starting from copied rules text or a rough summary rather than a spec, prefer the intake workspace:

```bash
python3 -m trader_factory.cli intake-workspace generic --output-dir /tmp/new_round_intake
python3 -m trader_factory.cli brief-to-spec /tmp/new_round_intake/round_brief.json --output /tmp/new_round_intake/spec.json --report-output /tmp/new_round_intake/brief_extraction.md
python3 -m trader_factory.cli validate-spec /tmp/new_round_intake/spec.json
```

That creates:

- `raw_brief.md`
- `round_brief.json`
- `spec.json`
- `brief_extraction.md`

The purpose is to reduce the amount of manual JSON authoring needed when the round first opens.
