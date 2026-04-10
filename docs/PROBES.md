# Probes

`TraderFactory` now includes a reusable execution-probe framework for research mode.

Core package:

- [trader_factory/probes](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/probes)

Current capabilities:

- standard DIAG event helpers in [logging.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/probes/logging.py)
- built-in probe specs in [specs.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/probes/specs.py)
- probe workspace generation in [scaffold.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/probes/scaffold.py)

## Probe Modes

The framework makes the baseline relationship explicit:

- `shadow`
  - run the candidate logic in shadow and log only the discrete differences
- `replacement`
  - replace the product sleeve with a dedicated probe trader
- `overlay`
  - keep the production sleeve and add tiny labeled probe actions on top

## Supported Probe Types

- `boundary`
  - for dormant-vs-live decision-boundary questions
- `passive_ladder`
  - for passive fill behavior by quote distance
- `aggressive_markout`
  - for context-specific taker markout questions

## Scaffold A Probe Workspace

Example:

```bash
python3 -m trader_factory.cli probe-scaffold aggressive_markout \
  /absolute/path/to/Traderv52.py \
  --name v52_range_buy_probe \
  --context range_buy \
  --output-dir /tmp/v52_range_buy_probe
```

Generated workspace files:

- `README.md`
- `probe.json`
- `submission_probe.py`
- `notes.md`

## Design Rule

The scaffold is intentionally honest:

- it creates a clean research workspace
- it standardizes event naming and analyzer expectations
- it does **not** claim to auto-convert a production bot into a finished submission probe

That last step is still strategy-specific and should be done deliberately by the agent or developer.

## Standard Event Envelope

Use these keys for every event when possible:

- `probe_id`
- `probe_kind`
- `event`
- `product`
- `ts`

For backward compatibility with the current analyzers, keep the historical short keys too when needed:

- `et`
- `p`

The helper in [logging.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/probes/logging.py) supports that directly through `make_event(...)`.

## Relationship To Diagnostics

The probe framework creates the research workspace and event schema.

The diagnostics package analyzes official outputs afterward:

- [boundary_probe.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/diagnostics/boundary_probe.py)
- [passive_ladder.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/diagnostics/passive_ladder.py)
- [aggressive_markout.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/diagnostics/aggressive_markout.py)

## Current Scope

What is implemented:

- probe registry
- event formatting
- workspace scaffolding
- research-mode documentation

What is not yet implemented:

- automatic source-to-probe rewriting of arbitrary baseline bots
- a full in-package catalog of historical probe bot implementations

Those are future additions on top of this framework, not missing basics.
