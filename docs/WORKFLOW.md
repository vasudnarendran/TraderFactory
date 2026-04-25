# Workflow

`TraderFactory` uses two explicit working modes.

## Development Mode

Use development mode when:

- the core mechanic is understood
- the change is a model improvement, not a simulator research question
- the objective is to build or optimize a production candidate

Typical work:

- capture the raw brief in an intake workspace when the round first opens
- work through `round_opening_checklist` and each product's `product_opening_checklist`
- convert `round_brief.json` into `spec.json`
- inspect `brief_extraction.md` so inferred fields stay auditable
- validate the round spec
- scaffold a baseline bot
- add or refine a strategy sleeve
- run deterministic replay
- run Monte Carlo robustness
- run focused optimization
- compare against the baseline
- apply an explicit promotion policy rather than relying on ad hoc judgment
- use `develop-cycle-imc` when you want TraderFactory to apply a standard local gate before consuming an official submission slot

## Research Mode

Use research mode when:

- official behavior does not match local expectations
- a feature seems dormant officially
- fill mechanics are unclear
- the right execution rule is not known yet

Typical work:

- boundary probes
- passive ladder probes
- aggressive markout probes
- official-log analysis
- discovery logging

## Switching Rule

The operating rule established in the current project is:

- stay in research mode while uncertainty is structural
- if a probe reveals a usable edge, switch into development mode
- implement the feature in the production line
- validate it
- return to research mode only if important uncertainty remains

This prevents endless half-research, half-development branches.

## Current CLI Mapping

Development mode:

```bash
python3 -m trader_factory.cli spec-template generic --output /tmp/new_round_spec.json

python3 -m trader_factory.cli intake-workspace generic --output-dir /tmp/new_round_intake

python3 -m trader_factory.cli brief-to-spec /tmp/new_round_intake/round_brief.json --output /tmp/new_round_intake/spec.json --report-output /tmp/new_round_intake/brief_extraction.md

python3 -m trader_factory.cli validate-spec /path/to/spec.json

python3 -m trader_factory.cli scaffold-project /path/to/spec.json

python3 -m trader_factory.cli gate-imc-set \
  --round-id 1 \
  --deterministic-min-total-delta 0.0 \
  --mc-min-mean-delta 0.0

python3 -m trader_factory.cli baseline-imc-set \
  --round-id 1 \
  --compare-bot /path/to/Baseline.py

python3 -m trader_factory.cli develop-cycle-imc /path/to/Candidate.py \
  --round-id 1
```

This runs:

1. local deterministic checks
2. local Monte Carlo checks
3. policy evaluation across the local metrics
4. official submission only if the gate policy passes, unless `--force-submit` is set
4. a final summary with both local and official verdicts

The baseline command is optional, but useful. Once set, `develop-cycle-imc` can reuse the stored local baseline bot and optional official baseline artifacts automatically.
The policy JSON lives under `configs/baselines/` and is treated as local machine state rather than committed project config.
The gate policy JSON lives under `configs/gates/` and defines the reusable promotion thresholds for the round.

For a safe local-only validation pass:

```bash
python3 -m trader_factory.cli develop-cycle-imc /path/to/Candidate.py --round-id 1 --dry-run
```

Research mode:

```bash
python3 -m trader_factory.cli probe-scaffold ...
python3 -m trader_factory.cli boundary-probe ...
python3 -m trader_factory.cli passive-ladder ...
python3 -m trader_factory.cli aggressive-markout ...
```
