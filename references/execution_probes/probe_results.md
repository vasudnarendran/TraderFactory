# Probe Results

This file records the concrete outcomes of the official execution probes so the information does not get lost between sessions.

## Probe 0: Decision-Boundary Probe

Bot:

- [Traderv55.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv55.py)

Goal:

- determine whether a shadow execution overlay actually changes any official discrete decision

Official outcome:

- final score tied `v52` exactly
- official trade path was unchanged
- shadow overlay produced `6` official boundary-change events
- all `6` changes were passive size only
- no quote prices changed
- no taker decisions changed

Key examples:

- short TOMATOES inventory around `18900-19300`: `sell_passive_qty 8/9 -> 7/8`
- long TOMATOES inventory around `67800-68000`: `buy_passive_qty 8/9 -> 7/8`

Conclusion:

- the overlay was live
- but it was too weak to affect official fills or PnL

## Probe 1: Passive Distance Ladder

Bot:

- [Traderv56.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv56.py)

Goal:

- measure official fill behavior by passive quote distance from the touch

Local outcome:

- the probe filled frequently locally
- `d0` was most active
- `d1` still filled meaningfully
- `d2` filled rarely but not never

Official outcome:

- submission-side TOMATOES fills: `0`
- submission-side EMERALDS fills: `33`
- TOMATOES final PnL: `0.0`
- official logs contained no `DIAG` events

Important implementation note:

- the missing `lp_summary` is partly explained by a real bug:
  [Traderv56.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv56.py) used `PROBE_ROUND_LENGTH = 1_000_000.0`, so the end summary threshold never triggered in the official `0-199900` timestamp window

Main research conclusion:

- the official simulator did not fill this style of tiny symmetric passive TOMATOES quoting at all
- therefore the local passive-fill model is materially too optimistic for this order class

## What These Two Probes Together Mean

Probe 0 plus Probe 1 narrow the problem a lot:

- size-only passive overlays are too weak
- pure tiny passive TOMATOES ladder quoting is not rewarded officially in the tested form

So the next useful probe should target:

- aggressive/taker decision quality by context
- or quote-price / marketability boundaries that are strong enough to move official fills

## Probe 2A: Aggressive Markout Probe, Rotating Contexts

Files:

- [Traderv57.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv57.py)
- [official_aggressive_markout_probe_report.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/tools/official_aggressive_markout_probe_report.py)

Official outcome:

- [reports/v57_aggressive_markout_probe_summary.txt](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v57_aggressive_markout_probe_summary.txt)
- [reports/v52_vs_v57_official_trade_quality_report.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v52_vs_v57_official_trade_quality_report.md)

What happened officially:

- `v57` tied `v52` exactly at `2636.171875`
- `activitiesLog` was identical to `v52`
- submission-side `tradeHistory` was identical to `v52`
- logs differed only because `v57` emitted one final `am_summary`

Probe-specific result:

- total probe events: `1`
- fill events: `0`
- summary events: `1`
- the summary recorded:
  - `range_buy available_count = 3`
  - `range_buy submitted_count = 0`
  - all other contexts had `0` submissions and `0` fills

Conclusion:

- the rotating-context design was too sparse
- this version did not answer the aggressive-markout question

## Probe 2B: Dedicated `range_buy` Probe

Files:

- [Traderv58.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv58.py)
- [official_aggressive_markout_probe_report.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/tools/official_aggressive_markout_probe_report.py)

Official outcome:

- [reports/v58_aggressive_markout_probe_summary.txt](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v58_aggressive_markout_probe_summary.txt)
- [reports/v52_vs_v58_official_trade_quality_report.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v52_vs_v58_official_trade_quality_report.md)

What happened officially:

- `v58` tied `v52` exactly at `2636.171875`
- `activitiesLog` was identical to `v52`
- submission-side `tradeHistory` was identical to `v52`
- logs differed only because `v58` emitted probe diagnostics

Probe-specific result:

- total probe events: `4`
- fill events: `3`
- summary events: `1`
- all three official probe fills were `range_buy`
- summary stats:
  - `available_count = 3`
  - `submitted_count = 3`
  - `filled_count = 3`
  - `avg_visible = -2.5`
  - `avg_fair = 1.5342`
  - `avg_margin = 0.8449`
  - `avg_m4 = 1.5`

The three official probe fills were:

- `27300 BUY 4993 x1`: `m4 = 1.0`
- `54700 BUY 4989 x1`: `m4 = 1.0`
- `59300 BUY 4984 x1`: `m4 = 2.5`

Conclusion:

- dedicated single-context probing works
- negative visible-edge `range_buy` TOMATOES trades can still be profitable on short-horizon markout
- the probe samples did not alter the `v52` official trade path, so this is clean tagging of baseline-quality opportunities rather than a new execution edge by itself

Implication for the next probe:

- run the symmetric dedicated sell-side context next, not another rotating multi-context probe

## Probe 2C: Dedicated `range_sell` Probe

Files:

- [Traderv59.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv59.py)
- [official_aggressive_markout_probe_report.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/tools/official_aggressive_markout_probe_report.py)

Official outcome:

- [reports/v59_aggressive_markout_probe_summary.txt](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v59_aggressive_markout_probe_summary.txt)
- [reports/v52_vs_v59_official_trade_quality_report.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v52_vs_v59_official_trade_quality_report.md)

What happened officially:

- `v59` tied `v52` exactly at `2636.171875`
- `activitiesLog` was identical to `v52`
- submission-side `tradeHistory` was identical to `v52`
- logs differed only because `v59` emitted one final summary

Probe-specific result:

- total probe events: `1`
- fill events: `0`
- summary events: `1`
- summary stats:
  - `range_sell available_count = 0`
  - `range_sell submitted_count = 0`
  - `range_sell filled_count = 0`

Conclusion:

- under the current `range_sell` definition, this context simply did not occur on the official `v52` path
- this is different from `v57`, where the context existed but the rotating design missed it
- the current symmetric sell-side question remains unanswered, because the selected sell-side context was too narrow or not representative of actual `v52` sell behavior

Implication for the next probe:

- do not keep probing this exact `range_sell` definition
- the next sell-side probe should target a sell context that is known to appear, likely a long-reduction or breakout-opposed sell class rather than generic `range_sell`
