# Optimization

`TraderFactory` now includes a local CMA-ES engine for source-patching optimizations.

Current entry point:

- [trader_factory/optimization/cmaes.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/optimization/cmaes.py)

CLI:

```bash
python3 -m trader_factory.cli cmaes configs/examples/v52_tight_cmaes.json
```

You can override the main search controls from the CLI:

```bash
python3 -m trader_factory.cli cmaes configs/examples/v52_tight_cmaes.json \
  --max-iter 1 \
  --population 4 \
  --parents 2 \
  --output-dir /tmp/traderfactory_cmaes_smoke
```

## What The Engine Does

The current optimizer is a regularized full-covariance CMA-ES modeled on the successful `v51` and `v52` optimization scripts.

It currently supports:

- patching source parameters inside named dict blocks such as `DEFAULT_TOMATOES_PARAMS`
- patching class constants through an explicit class/field location
- multi-day deterministic evaluation
- objective penalties for:
  - regressions relative to baseline scores
  - uneven gains across days
  - excessive drift away from source defaults
- writing:
  - best bot source
  - machine-readable JSON summary
  - markdown report with parameter deltas and generation history

## Config Schema

Top-level fields:

- `name`: human-readable experiment name
- `source_bot`: source trader file to optimize
- `default_dict_block`: optional default dict block for shorthand parameter entries
- `baselines`: day-to-score map used for baseline checks and penalties
- `search`: CMA-ES controls
- `penalties`: objective penalty weights
- `output_prefix`: artifact prefix
- `parameters`: list of tunable parameters

### Parameter Entry

Minimal dict-block form:

```json
{
  "name": "BASE_TAKE_EDGE",
  "lower": 0.48,
  "upper": 0.72
}
```

This uses the config-level `default_dict_block` and assumes the key name matches `name`.

Explicit location form:

```json
{
  "name": "BOOK_STEP_WEIGHT",
  "lower": 0.6,
  "upper": 1.0,
  "location": {
    "type": "dict_block",
    "container": "DEFAULT_TOMATOES_PARAMS",
    "key": "BOOK_STEP_WEIGHT"
  }
}
```

Class constant form:

```json
{
  "name": "MAX_QUOTE_EDGE",
  "lower": 1.0,
  "upper": 3.0,
  "location": {
    "type": "class_constant",
    "class_name": "TomatoesTrader",
    "key": "MAX_QUOTE_EDGE"
  }
}
```

## Output Layout

By default, outputs go to:

```text
generated/optimization/<output_prefix>/
```

Artifacts:

- `<output_prefix>_best.json`
- `<output_prefix>_report.md`
- `bots/<source_stem>_best.py`

## Current Scope

What is already local to `TraderFactory`:

- config loading
- source patching
- deterministic evaluation
- CMA-ES loop
- artifact writing

What is still missing:

- sweep runners
- alternative objectives such as inventory-aware or trade-quality-aware scoring
- direct integration with Monte Carlo robustness as an optimizer objective

Those should be added on top of this engine rather than by creating new version-specific scripts.
