# Workflow

`TraderFactory` uses two explicit working modes.

## Development Mode

Use development mode when:

- the core mechanic is understood
- the change is a model improvement, not a simulator research question
- the objective is to build or optimize a production candidate

Typical work:

- scaffold a baseline bot
- add or refine a strategy sleeve
- run deterministic replay
- run Monte Carlo robustness
- run focused optimization
- compare against the baseline

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

