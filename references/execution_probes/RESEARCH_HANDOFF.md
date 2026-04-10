# Execution Research Handoff

This note is the compact handoff for the current official execution-model research.

The goal of this phase is not to squeeze more micro-tuning out of `v52`. The goal is to learn which execution changes actually cross official decision boundaries and which execution behaviors the official simulator rewards.

The canonical running discovery log is:

- [DISCOVERIES.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/DISCOVERIES.md)

## 1. Where The Bot Line Stands

- [Traderv37.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Bots/Traderv37.py) was the original strong official baseline.
- [Traderv51.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Bots/Traderv51.py) is the faithful clean reconstruction of `v37`.
- [Traderv52.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Bots/Traderv52.py) is the current best clean official result.

Official scores already established:

- `v37`: `2627.875`
- `v52`: `2636.171875`

That gain is real, but small. It came entirely from TOMATOES execution.

## 2. What Was Learned Before The Probe Stage

The most important pre-probe findings are preserved in:

- [docs/execution_research_phase1.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/docs/execution_research_phase1.md)
- [reports/v37_vs_v52_official_trade_quality_report.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v37_vs_v52_official_trade_quality_report.md)
- [reports/v37_vs_v42_official_trade_quality_report.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v37_vs_v42_official_trade_quality_report.md)
- [reports/v37_vs_v46_official_trade_quality_report.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v37_vs_v46_official_trade_quality_report.md)
- [reports/v52_vs_v54_official_trade_quality_report.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v52_vs_v54_official_trade_quality_report.md)

The reliable conclusions were:

- meaningful edge is still TOMATOES execution
- over-aggressive execution is the clearest way to lose quickly
- reducing bad fills alone is not enough if monetization falls
- many execution overlays never become live officially
- local Monte Carlo is useful for robustness, but cannot answer the official fill-model question by itself

## 3. Probe 0 Result

Probe 0 bot:

- [bots/Traderv55.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv55.py)

Probe 0 tool:

- [tools/official_boundary_probe_report.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/tools/official_boundary_probe_report.py)

Official result summary:

- `v55` was behaviorally identical to `v52`
- the shadow overlay was live officially
- but it changed only passive size
- it did not change quote prices
- it did not change taker decisions
- therefore it did not change fills or PnL

Copied summary:

- [reports/v55_boundary_probe_summary.txt](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v55_boundary_probe_summary.txt)

Why this matters:

- it proved that “inactive officially” and “too weak to affect outcomes officially” are different cases
- it also showed that size-only overlays are probably a low-value direction

## 4. Probe 1 Result

Probe 1 bot:

- [bots/Traderv56.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv56.py)

Probe 1 tool:

- [tools/official_passive_ladder_report.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/tools/official_passive_ladder_report.py)

Probe 1 local result:

- the passive ladder filled frequently locally at `d0`
- `d1` still filled meaningfully
- `d2` filled rarely but not never

Probe 1 official result:

- submission-side TOMATOES fills: `0`
- submission-side EMERALDS fills: `33`
- TOMATOES PnL: `0.0`
- all official log rows had empty `lambdaLog` / `sandboxLog`

What is proven from that run:

- a pure tiny passive TOMATOES ladder at the touch and behind the touch got zero official fills
- the local passive-fill model is materially too optimistic for this style of order

What went wrong in the probe implementation:

- [bots/Traderv56.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv56.py) uses `PROBE_ROUND_LENGTH = 1_000_000.0`
- the official run only reaches about `199900`
- so the end-of-round `lp_summary` condition never fired

That is a real bug, but it does not change the main conclusion because there were no official TOMATOES fills to summarize anyway.

## 5. Most Important Current Facts

These are the facts to trust going into the next probe:

1. `v52` should remain the live strategy baseline.
2. Small float-level execution overlays often fail to move any official discrete decision.
3. Passive-size-only overlays are too weak to matter.
4. Pure tiny passive TOMATOES ladder quoting did not get official fills at all.
5. Therefore future research should focus on quote-price / marketability boundaries or controlled aggressive participation, not passive-size nudges.

## 6. What Not To Do Next

Avoid these next:

- another size-only participation controller
- another tiny passive-distance experiment in the same shape as `v56`
- another broad complexity branch like the old `v42-v50` family
- another local-only optimizer pass around `v52`

## 7. Best Next Probe

Best next move:

- build Probe 2 off `v52`
- test tiny aggressive TOMATOES trades in mutually exclusive contexts
- record which negative visible-edge trades are still good on short-horizon markout

Current Probe 2 files:

- [bots/Traderv57.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv57.py)
- [bots/Traderv58.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv58.py)
- [tools/official_aggressive_markout_probe_report.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/tools/official_aggressive_markout_probe_report.py)

What `v57` does:

- keeps `v52` baseline TOMATOES logic
- adds only tiny `1`-lot aggressive probe orders on top of the normal flow
- rotates through context labels
- emits `am_fill` and `am_summary` diagnostics

Official Probe 2 result:

- `v57` tied `v52` exactly
- it emitted only a final `am_summary`
- it collected zero official taker samples
- the summary showed `range_buy` opportunities existed (`available_count = 3`) but none were submitted

Implication:

- the rotating-context collection design is too sparse
- the next aggressive probe should run one context per submission or submit the first eligible candidate instead of rotating

Current follow-up draft:

- [bots/Traderv58.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv58.py)
- [bots/Traderv59.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv59.py)

What changed in `v58`:

- same probe family as `v57`
- dedicated to one context only: `range_buy`
- no context rotation

Local validation on `v58`:

- it now collects many local `range_buy` probe fills
- it emits `am_fill` and `am_summary`
- it is the correct next official probe to submit

Official `v58` result:

- `v58` tied `v52` exactly
- it collected `3` official `range_buy` samples
- average visible edge was `-2.5`
- average 4-step markout was `+1.5`
- the probe did not alter the `v52` official trade path

Meaning:

- `range_buy` is now a validated positive context
- the next dedicated aggressive-markout question should be the symmetric sell-side case

Current sell-side follow-up:

- [bots/Traderv59.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv59.py)

What changed in `v59`:

- same dedicated single-context structure as `v58`
- context switched from `range_buy` to `range_sell`

Local validation on `v59`:

- it collects many local `range_sell` probe fills
- it emits `am_fill` and `am_summary`
- it is the correct next official submission for the symmetric sell-side question

Official `v59` result:

- `v59` tied `v52` exactly
- it emitted only a final `am_summary`
- `range_sell available_count = 0`
- it collected zero official sell-side samples

Meaning:

- the current symmetric `range_sell` definition does not occur on the official `v52` path
- the next sell-side probe should be derived from observed sell behavior, not just from buy/sell symmetry

The clean contexts to test are already described in:

- [docs/execution_probe_suite.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/docs/execution_probe_suite.md)

The short version:

- `range + short cover`
- `range + long reduction`
- `trend-aligned buy`
- `trend-aligned sell`
- `breakout-opposed exit`

The probe must keep sizes tiny, log context explicitly, and preserve EMERALDS behavior.

## 8. Files Another Agent Should Read First

1. [DISCOVERIES.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/DISCOVERIES.md)
2. [RESEARCH_HANDOFF.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/RESEARCH_HANDOFF.md)
3. [docs/probe_results.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/docs/probe_results.md)
4. [docs/execution_probe_suite.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/docs/execution_probe_suite.md)
5. [bots/Traderv55.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv55.py)
6. [bots/Traderv56.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv56.py)
7. [tools/official_boundary_probe_report.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/tools/official_boundary_probe_report.py)
8. [tools/official_passive_ladder_report.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/tools/official_passive_ladder_report.py)
