# Official Execution Probe Suite

This is the recommended probe sequence for learning the official simulator rather than blindly tweaking `v52`.

The probes below are ordered by expected information gain.

## Probe 0: Decision-Boundary Probe

### Goal

Detect whether a candidate overlay is actually changing:
- quote prices
- quote sizes
- taker thresholds
- or take/no-take decisions

### Why this comes first

`v53` and `v54` both showed that a concept can look sensible locally, improve Monte Carlo, and still be completely dormant officially.

### Design

Start from `v52` and add only diagnostic logging:
- computed guard / overlay strength
- baseline quote and candidate quote
- baseline size and candidate size
- baseline take threshold and candidate threshold
- whether the candidate changed any discrete order actually submitted

Only log when:
- the candidate changes a rounded quote
- the candidate changes submitted size
- the candidate changes a take/no-take decision

### Success criterion

If the log shows zero discrete changes on official runs, kill the branch immediately.

## Probe 1: Passive Distance Ladder

### Goal

Measure how fill frequency and short-horizon markout change as a function of quote distance from touch.

### Hypothesis

The current team still does not know how much the official simulator rewards:
- best-bid / best-ask quotes
- one-tick-better monetization
- deeper passive levels

This matters because `v52`'s real gain over `v37` included a couple of one-tick better passive sells.

### Design

Build a TOMATOES-focused probe bot that:
- keeps inventory small
- only uses tiny quote sizes
- posts passive orders at a small fixed ladder relative to touch

Suggested ladder families:
- buy at `best_bid`, `best_bid - 1`, `best_bid - 2`
- sell at `best_ask`, `best_ask + 1`, `best_ask + 2`

Rotate which ladder is active by timestamp bucket so the fills are attributable.

### What to log

- timestamp
- side
- posted price
- price distance from touch
- whether the order filled
- fill quantity
- current spread
- current mid
- markout after 1 / 4 / 8 steps

### Questions answered

- Does one-tick-better passive pricing still fill often enough?
- Are touch quotes overexposed to adverse selection?
- Which distances produce the best markout-adjusted execution?

## Probe 2: Aggressive Markout Probe

### Goal

Learn when aggressive TOMATOES trades with negative visible edge are still directionally good.

### Why this matters

Past official evidence showed:
- some ask-lifting short-cover buys looked bad versus current mid but had positive short-horizon markout
- some late bid-hitting sells were clearly harmful

So "negative visible edge" is not enough by itself.

### Design

Build a small-sample taker probe that only triggers when:
- visible edge is slightly negative
- size is tiny
- one selected context flag is active

Probe contexts should be mutually exclusive and simple:
- `range + short cover`
- `range + long reduction`
- `trend-aligned buy`
- `trend-aligned sell`
- `breakout-opposed exit`

### What to log

- context label
- side
- visible edge
- fair edge
- flow / breakout / regime snapshot
- markout 1 / 4 / 8

### Questions answered

- Which negative-edge aggressive trades are actually worth paying for?
- Are good covers asymmetric by side?
- Is the harmful class mainly late sell exits, as earlier diagnostics suggested?

## Probe 3: Passive Monetization Probe

### Goal

Measure when a one-tick more ambitious passive quote is worth it.

### Why this matters

The `v37 -> v52` improvement included:
- `17400 SELL 5008 -> 5009`
- `59400 SELL 4990 -> 4991`
- `161600 BUY 4978 -> 4977`

That suggests the remaining edge may partly live in selective one-tick monetization.

### Design

Choose a narrow context only:
- already aligned with target
- non-urgent inventory
- favorable short-horizon signal agreement

Alternate between:
- baseline passive price
- baseline plus one tick improvement

Keep size tiny so the experiment measures pricing, not inventory risk.

### What to log

- context label
- baseline price
- probe price
- whether fill occurred
- markout after fill
- time-to-fill proxy

### Questions answered

- When does better passive monetization actually survive the official fill model?
- Is there a consistent sell-side advantage?

## Probe 4: Inventory-Unwind Urgency Probe

### Goal

Learn whether late unwind pressure should be handled by:
- more aggressive crossing
- better passive pricing
- or simply smaller earlier inventory buildup

### Why this is lower priority

We already know broad unwind overlays can hurt.
This probe should only happen after the earlier fill-model questions are clearer.

### Design

Use a narrow inventory band experiment:
- when TOMATOES inventory exceeds a threshold late in the round
- alternate between passive-only unwind and tiny capped aggressive unwind

### Questions answered

- Is late inventory actually the problem?
- Or is earlier execution quality the bigger driver?

## Probe Bot Rules

All probe bots should obey these rules:

1. Only ask one question at a time.
2. Keep TOMATOES sizes tiny.
3. Keep EMERALDS unchanged or disabled as much as possible.
4. Log the experiment bucket or context explicitly.
5. Prefer many small comparable observations over a few large bets.
6. Never mix a probe with a full candidate strategy change.

## Minimum Tooling for Each Probe

Use:
- [Analysis/official_trade_quality_report.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Analysis/official_trade_quality_report.py)
- [Analysis/official_diag_report.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Analysis/official_diag_report.py) when a probe emits `DIAG` events
- [Analysis/v52_monte_carlo_robustness.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Analysis/v52_monte_carlo_robustness.py) for local robustness checks
- [Analysis/monte_carlo_sensitivity_report.py](/Users/vasudravinarendran/Documents/Prosperity/Prosperity/Analysis/monte_carlo_sensitivity_report.py) for postmortem analysis

## Recommended Order

1. Decision-boundary probe
2. Passive distance ladder
3. Aggressive markout probe
4. Passive monetization probe
5. Inventory-unwind urgency probe

This order is deliberate:
- first confirm that future overlays are actually live
- then learn the passive fill model
- then learn the aggressive markout asymmetries
- only after that build another serious strategy candidate
