# Generation

`TraderFactory` can now scaffold a capability-aware baseline trader project from a competition spec.

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
- `experiments/README.md`
- `experiments/cmaes_template_<product>.json`
- `research/README.md`
- `research/probe_targets.md`

## Design Goal

This is a baseline project scaffold, not a full auto-trader generator.

It is meant to:

- copy the structured round spec
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

- project directory scaffolding
- per-product archetype selection
- runnable baseline sleeves for anchored, simple market-making, and directional microstructure products
- copied spec and plan
- baseline parameter and metadata file
- experiment template generation
- research template generation

What is still missing:

- automatic sleeve code generation from capability sets
- richer sleeve implementations for pair, options, and informed-flow products
- generated official-submission packaging from each project
