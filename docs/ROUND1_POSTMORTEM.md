# Round 1 Postmortem — Key Discoveries

## Final result

| Submission | Bot | Total | ASH | IPR |
|---|---|---|---|---|
| 111269 | v2 | 9,985 | 2,471 | 7,514 |
| 118848 | v4_final | **9,994** | 2,480 | 7,514 |
| 127199 | v5 (IW=3.4, BASE=7.5) | 9,407 | 1,893 | 7,514 |
| 131578 | v7 (HMM + dual fair, CMA-ES) | 9,458 | 1,944 | 7,514 |
| 142422 | v8 (v4_final + dual fair, no CMA-ES) | 9,407 | 1,893 | 7,514 |

Best official: **9,994** (v4_final, submission 118848).

---

## Discovery 1 — Adverse selection does not apply to mean-reverting assets

### What we believed

ASH_COATED_OSMIUM passive fills had an "adverse selection" problem.
Fill decomposition of submission 118848 showed:
- 47 winning fills: ALL aggressive sweep, avg edge +7.38 vs mid
- 30 losing fills: ALL passive, avg edge −3.80 vs mid at fill time

We interpreted the 30 passive fills as adversely selected: resting bids placed
above market mid being hit by informed sellers. The fix we designed: widen
passive quote edge (BASE_EDGE 2.0 → 7.5) so bids sit below mid in bearish
books, eliminating those fills.

### What actually happened

Every attempt to suppress passive fills produced an identical regression of
approximately −587 PnL:

```
v5  (IMBALANCE_WEIGHT=3.4, BASE_EDGE=7.5)           −587
v7  (HMM gate + dual fair value, CMA-ES optimised)   −536
v8  (v4_final sweep locked, only BASE_EDGE=7.5)      −587
```

The regression magnitude was the same regardless of whether we changed
IMBALANCE_WEIGHT, added an HMM, or ran CMA-ES. The only common factor
in all three regressions: BASE_EDGE widened to 7.5, reducing passive fill volume.

### The root cause — wrong mental model

**Adverse selection requires permanently informed traders.** In equities,
an informed seller knows the stock will fall permanently and hits your bid
knowing you will lose. The "edge vs mid at fill time" metric correctly captures
that loss.

ASH_COATED_OSMIUM is anchored at 10000 and mean-reverts. There are no
permanently informed traders. When the book is bearish (heavy sell imbalance),
the mid dips temporarily — and then reverts. A passive bid filled at "mid+3.8"
during a temporary bearish dip is actually a good fill: we bought the dip and
the position became profitable as the price reverted.

The "avg edge −3.80 vs mid at fill time" metric only measures the fill price
relative to mid at the instant of the fill. It does not capture the subsequent
price trajectory. For a mean-reverting asset, this metric is misleading: a fill
that looks adverse at t=0 is often profitable by t=100.

### Corrected interpretation

| Metric | What it measures | Reliable for mean-reverting asset? |
|---|---|---|
| Edge vs mid at fill time | Immediate fill quality | No — ignores reversion |
| Net PnL of position over full lifecycle | True trade profitability | Yes |

The 30 "adverse" fills were contributing approximately +587 PnL to the total
across the 3-day evaluation when the full trade lifecycle is accounted for.
Eliminating them eliminated that PnL.

### Rule going forward

> **Do not apply adverse selection analysis to mean-reverting anchored assets.**
> Passive fills that appear to buy above momentary mid are often profitable
> because the asset reverts. The correct measure of fill quality is the
> realised PnL of the position, not the edge vs mid at fill time.

For assets with genuine informed traders (trending, news-driven, supply-shock),
adverse selection analysis applies normally.

---

## Discovery 2 — Local CMA-ES cannot reliably optimise passive quote parameters

### What we believed

Local CMA-ES backtest scores would guide optimisation of all parameters
including passive quote placement (BASE_EDGE, IMBALANCE_WEIGHT).

### What happened

The local backtester models passive fills at approximately 10% of the
official exchange rate. This creates a systematic distortion:

- CMA-ES sees fewer passive fills locally → passive parameters have less
  impact locally → optimiser focuses on aggressive take parameters
- When it does optimise passive parameters, it learns to be conservative
  (wide quotes) because locally, passive fills are rare and their
  adverse-selection cost appears proportionally large
- On the official exchange, passive fills occur at full rate, so reducing
  them through wide quotes causes large PnL loss

This explains why CMA-ES consistently found conservative passive params
(BASE_EDGE=7.5, MAX_SWEEP_LEVELS=1, SWEEP_SIZE=3) that looked good locally
but regressed officially.

### Rule going forward

> **Lock passive quote parameters at proven official values. Never CMA-ES
> optimise them.** Only use CMA-ES for aggressive take parameters
> (TAKE_L* edges, MAX_SWEEP_LEVELS, SWEEP_SIZE) where local/official
> transfer rate is ~100%.

---

## Discovery 3 — HMM and ORIA are right techniques, wrong asset

### HMM (Hidden Markov Model)

Built and implemented in trader_v7.py: 2-state online EM with exponential
forgetting, warm-started from fill analysis priors. The implementation is
correct. The application was wrong.

HMM regime detection suppresses passive bids when P(informed state) is high.
For a mean-reverting asset, this removes profitable dip-buying. For assets
with genuine regime dynamics (trending, supply shocks, news events), HMM
adds real value.

**Reuse:** Apply `HMMRegimeDetector` from trader_v7.py to future round
products that have genuine regime-switching behaviour.

### ORIA (Orthogonal Risk Integrated Alpha)

Never implemented in Round 1 — we were blocked by the ASH regression
loop before reaching IPR improvements.

ORIA replaces fixed-weight signal blending (0.60×trend + 0.12×mid + ...)
with weights derived from Gram-Schmidt orthogonalisation and IC/σ_IC
computed on historical data. Requires at least 10+ days of data for
reliable IC estimation — 3 days of Round 1 data is insufficient.

**Reuse:** Apply to IPR-style products in future rounds once sufficient
historical data exists (Round 3+).

---

## What worked

- **DRIFT=0.0026009226** — proven empirically. Inflated drift (vs calibrated
  0.001) drives aggressive early accumulation that captures the IPR trend.
  Lock this value in all future IPR-style bots.
- **Multi-level aggressive sweep** — MAX_SWEEP_LEVELS=4, SWEEP_SIZE=20,
  TAKE_L1_EDGE=0.62 produced 47 winning fills at avg +7.38 edge. These
  transfer at ~100% from local to official.
- **Passive quoting at BASE_EDGE=2.0** — produces profitable fills through
  mean-reversion dip-buying. Do not widen.
- **SOFT_LIMIT=70** — preserves aggressive sweep behaviour at high inventory.
  Partner's SOFT_LIMIT=28 was unnecessarily restrictive for v4_final's strategy.

## What did not help (and why)

- **IMBALANCE_WEIGHT=3.4** (partner value) — Correct for a stock-like asset.
  Wrong for ASH which does not have permanent informed flow.
- **BASE_EDGE=7.5** — Removes profitable mean-reversion passive fills.
- **HMM suppression of passive bids** — Same root cause as above.
- **CMA-ES on passive params** — Local/official transfer gap makes this
  unreliable.

---

## Recommended starting point for future similar products

If a future round introduces an anchored mean-reverting product:

1. Start from trader_v4_final.py
2. Do not change BASE_EDGE, SOFT_LIMIT, or IMBALANCE_WEIGHT
3. Only CMA-ES the aggressive take parameters (TAKE_L* edges, SWEEP_SIZE,
   MAX_SWEEP_LEVELS)
4. Do not interpret "edge vs mid at fill time" as fill quality — look at
   net position PnL instead

If a future round introduces a trending product:

1. Start from the IPR archetype in trader_v4_final.py
2. Lock DRIFT calibration empirically (submit with different drift values,
   observe which accumulates position fastest early in the day)
3. Consider HMM for regime detection if the trend has distinct accelerating
   vs ranging phases
4. Consider ORIA for signal weighting once 10+ days of data are available
