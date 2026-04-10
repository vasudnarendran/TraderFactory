# Discoveries

This file is the canonical running log of confirmed execution-research discoveries.

Rule going forward:

- every new official execution finding should be recorded here
- each entry should state whether it is a confirmed fact or an inference
- each entry should link back to the probe, report, or submission that supports it

This file is intentionally higher signal than the raw probe reports. It should read like a durable research notebook, not a changelog.

## Confirmed Discoveries

### D-001: `v52` is a real official improvement over `v37`

Status:

- confirmed

Evidence:

- `v37` official score: `2627.875`
- `v52` official score: `2636.171875`
- source comparison: [reports/v37_vs_v52_official_trade_quality_report.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v37_vs_v52_official_trade_quality_report.md)

What this means:

- the clean reconstruction line was worthwhile
- the current best known edge still comes from TOMATOES execution, not EMERALDS

### D-002: Small float-level overlays often do not cross official decision boundaries

Status:

- confirmed

Evidence:

- earlier overlays like `v53` and `v54` were officially dormant versus `v52`
- supporting discussion preserved in [docs/execution_research_phase1.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/docs/execution_research_phase1.md)

What this means:

- future branches must be checked for official liveness early
- local improvements alone are not enough to justify more tuning

### D-003: A dormant official branch can still be live internally, but too weak to affect fills

Status:

- confirmed

Evidence:

- Probe 0 bot: [bots/Traderv55.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv55.py)
- Probe 0 summary: [reports/v55_boundary_probe_summary.txt](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v55_boundary_probe_summary.txt)

What was observed:

- the shadow overlay produced `6` official boundary-change events
- all `6` were passive size changes only
- no quote-price changes occurred
- no taker decision changes occurred
- official fills and PnL were unchanged

What this means:

- “inactive” and “too weak to matter” are different cases
- passive-size-only overlays are probably not a productive direction

### D-004: The local backtester materially overestimates this class of pure passive TOMATOES fill

Status:

- confirmed

Evidence:

- Probe 1 bot: [bots/Traderv56.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv56.py)
- Probe 1 summary: [docs/probe_results.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/docs/probe_results.md)

What was observed:

- locally, the passive ladder filled frequently at `d0`, meaningfully at `d1`, and occasionally at `d2`
- officially, the same probe got `0` submission-side TOMATOES fills
- official TOMATOES PnL stayed `0.0`

What this means:

- pure tiny symmetric passive TOMATOES quoting cannot be trusted from local fill results alone
- future probes should emphasize quote-price / marketability boundaries or controlled aggression

### D-005: The remaining edge is still primarily a TOMATOES execution problem

Status:

- confirmed

Evidence:

- [reports/v37_vs_v52_official_trade_quality_report.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v37_vs_v52_official_trade_quality_report.md)
- [docs/execution_research_phase1.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/docs/execution_research_phase1.md)

What was observed:

- EMERALDS stayed flat across the main winning comparison
- `v52`’s official gain over `v37` came from a small set of better TOMATOES executions

What this means:

- EMERALDS should stay mostly frozen during this phase
- most future research budget should be spent on TOMATOES execution quality and official fill behavior

### D-006: A rotating aggressive-context probe can still fail to collect any official samples

Status:

- confirmed

Evidence:

- Probe 2 bot: [bots/Traderv57.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv57.py)
- Probe 2 summary: [reports/v57_aggressive_markout_probe_summary.txt](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v57_aggressive_markout_probe_summary.txt)
- direct comparison to `v52`: [reports/v52_vs_v57_official_trade_quality_report.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v52_vs_v57_official_trade_quality_report.md)

What was observed:

- `v57` tied `v52` exactly
- official `activitiesLog` and submission-side fills were unchanged
- the probe emitted only one final `am_summary`
- that summary showed `range_buy available_count = 3` but `submitted_count = 0`
- there were zero official probe fills

What this means:

- the aggressive-markout question is still unanswered
- rotating across multiple sparse contexts in a single run is too weak a collection design
- the next taker probe should either target one context per run or submit the first eligible candidate instead of waiting for a rotation match

### D-007: Negative visible-edge `range_buy` TOMATOES trades can still be good officially

Status:

- confirmed

Evidence:

- Probe 2B bot: [bots/Traderv58.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv58.py)
- Probe 2B summary: [reports/v58_aggressive_markout_probe_summary.txt](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v58_aggressive_markout_probe_summary.txt)
- direct comparison to `v52`: [reports/v52_vs_v58_official_trade_quality_report.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v52_vs_v58_official_trade_quality_report.md)

What was observed:

- `v58` collected `3` official `range_buy` samples
- all `3` were buys with average visible edge `-2.5`
- average fair edge was `+1.5342`
- average 4-step markout was `+1.5`
- per-sample `m4` values were `1.0`, `1.0`, and `2.5`

What this means:

- paying the ask is not automatically bad in TOMATOES range conditions
- at least one clean class of negative visible-edge buy is directionally good on the official simulator
- the execution problem is more nuanced than “avoid all negative visible-edge aggressive trades”

### D-008: The current dedicated `range_sell` definition does not appear on the official `v52` path

Status:

- confirmed

Evidence:

- Probe 2C bot: [bots/Traderv59.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/bots/Traderv59.py)
- Probe 2C summary: [reports/v59_aggressive_markout_probe_summary.txt](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v59_aggressive_markout_probe_summary.txt)
- direct comparison to `v52`: [reports/v52_vs_v59_official_trade_quality_report.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/reports/v52_vs_v59_official_trade_quality_report.md)

What was observed:

- `v59` tied `v52` exactly
- official `activitiesLog` and submission-side fills were unchanged
- the probe emitted only a final `am_summary`
- that summary showed `range_sell available_count = 0`

What this means:

- the current symmetric `range_sell` context is not the right sell-side lens for the official `v52` path
- a lack of samples here does not prove sell-side negative-edge aggression is good or bad
- it only proves this particular sell-side definition is not occurring in the official baseline path

## Strong Inferences

These are not direct facts from the simulator, but they are the best current interpretations of the evidence.

### I-001: Passive-size changes are unlikely to be enough by themselves

Status:

- inference

Why:

- Probe 0 crossed only passive-size boundaries and still produced no official path change
- Probe 1 showed pure passive TOMATOES quoting can be completely starved of fills

Working implication:

- future execution probes should prefer quote-price changes or controlled taker sampling over size-only overlays

### I-002: The next likely gains require understanding when paying the spread is justified

Status:

- inference

Why:

- the passive route looks much weaker officially than locally
- `v52`’s gain over `v37` was small and execution-specific
- earlier diagnostics already showed some negative visible-edge aggressive trades were still directionally good

Working implication:

- Probe 2 and similar aggressive markout probes are the right next class of experiment

### I-003: For execution probes, sample collection reliability matters as much as probe purity

Status:

- inference

Why:

- `v57` kept the strategy path clean but gathered zero official samples
- an execution probe that is too selective does not answer the research question even if it is methodologically neat

Working implication:

- future probes should be designed to guarantee some official observations, even if that means narrowing the context and running multiple dedicated submissions

### I-004: The symmetric sell-side range case is the next highest-value question

Status:

- inference

Why:

- dedicated `range_buy` probing produced clear positive evidence
- earlier diagnostics from other branches suggested some sell-side exits were the harmful class
- the best next disambiguation is to test the comparable sell-side context directly

Working implication:

- the next dedicated probe should target `range_sell`

### I-005: The next sell-side probe should be defined from observed sell behavior, not from symmetry alone

Status:

- inference

Why:

- `range_buy` produced usable official samples
- the naive symmetric `range_sell` definition produced none
- official sell behavior in `v52` may be concentrated in narrower classes like long reduction or breakout-opposed exits

Working implication:

- design the next sell-side probe around contexts that are known to appear or were previously implicated in harmful behavior

## Open Questions

### Q-001

Which negative visible-edge TOMATOES taker contexts are actually profitable on short-horizon markout?

Planned answer:

- partially answered:
  - `range_buy` looks positive
- next:
  - redesigned sell-side probe based on observed `v52` sell contexts

### Q-002

Is there a selective one-tick monetization edge that survives the official fill model?

Planned answer:

- only after aggressive-context quality is better understood

### Q-003

How harsh is the official passive queue model at the touch versus price-improved passive quotes?

Current status:

- partially informed by Probe 1
- not fully answered yet because the tested passive probe was too starved to give a distance curve officially

## Update Policy

When a new probe result arrives:

1. add the raw result to [docs/probe_results.md](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Research/execution_probes/docs/probe_results.md)
2. if it changes what we believe, add or update an entry here
3. link the evidence source directly
4. mark whether the claim is confirmed or only inferred
