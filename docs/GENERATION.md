# Generation

`TraderFactory` can now scaffold a baseline trader project from a competition spec.

Entry point:

- [trader_factory/generation/project.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/generation/project.py)

CLI:

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
- `plan.md`
- `params.py`
- `trader.py`
- `notes.md`

## Design Goal

This is a baseline project scaffold, not a full auto-trader generator.

It is meant to:

- copy the structured round spec
- preserve the generated round plan
- create a readable multi-product baseline trader skeleton
- keep the next development step concrete

It is not meant to:

- invent a final strategy automatically
- replace deliberate model design
- hide product logic inside a giant framework

## Current Scope

What is implemented:

- project directory scaffolding
- per-product class skeletons
- copied spec and plan
- baseline parameter and metadata file

What is still missing:

- automatic sleeve code generation from capability sets
- generated research/development experiment configs per product
- automatic integration of optimizer configs and probe configs into each generated project
