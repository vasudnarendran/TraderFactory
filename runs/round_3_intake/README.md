# Intake Workspace

This workspace is the bridge between a raw round brief and a validated competition spec.

## Files

- `raw_brief.md`: paste or summarize the raw round brief here
- `round_brief.json`: structured intake workbook for the round
- `spec.json`: machine-readable spec generated from `round_brief.json`
- `brief_extraction.md`: transparent report of fields inferred during brief-to-spec extraction

## Workflow

1. Paste the raw round brief into `raw_brief.md`.
2. Work through `round_opening_checklist` and each product's `product_opening_checklist` inside `round_brief.json`.
3. Fill `round_brief.json` with concrete facts, helper hints, mechanic hypotheses, and open questions.
4. Mark checklist items as `done`, `blocked`, or `n/a` as evidence becomes available.
5. Regenerate the spec:

```bash
python3 -m trader_factory.cli brief-to-spec ./round_brief.json --output ./spec.json --report-output ./brief_extraction.md
```

6. Validate the spec:

```bash
python3 -m trader_factory.cli validate-spec ./spec.json
```

7. Scaffold only after blocked findings are fixed:

```bash
python3 -m trader_factory.cli scaffold-project ./spec.json
```

Selected profile: `generic`.
