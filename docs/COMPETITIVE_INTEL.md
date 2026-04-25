# Competitive Intelligence

This document consolidates findings from top-team write-ups, GitHub repositories, and community analysis across Prosperity 1, 2, and 3. It is structured as an actionable guideline for improving rank, not a survey of what other teams did.

Sources are named inline. All repositories are publicly available on GitHub.

---

## Primary Sources

| Team | Placement | Round | Repository |
|---|---|---|---|
| Frankfurt Hedgehogs | 2nd global | P3 | github.com/TimoDiehm/imc-prosperity-3 |
| CMU Physics | 7th global, 1st USA | P3 | github.com/chrispyroberts/imc-prosperity-3 |
| Alpha Animals | 9th global, 2nd USA | P3 | github.com/CarterT27/imc-prosperity-3 |
| Theta Drip | 10th global | P3 | github.com/YBansal95/imc-prosperity-3 |
| Linear Utility | 2nd global | P2 | github.com/ericcccsliu/imc-prosperity-2 |
| jmerle | 9th global | P2 | github.com/jmerle/imc-prosperity-2 |
| Rank 13 | 13th global | P2 | github.com/pe049395/IMC-Prosperity-2024 |
| Stanford Cardinal | 2nd global | P1 | github.com/ShubhamAnandJain/IMC-Prosperity-2023-Stanford-Cardinal |
| Ding Crab | 28th algo | P3 | github.com/angus4718/imc-prosperity-3-public |
| AlphaBaguette | Top 1% | P3 | github.com/Sylvain-Topeza/imc-prosperity-3 |

---

## 1. The Execution Loop That Every Top Team Uses

The single most consistent finding across all write-ups: every top-10 team independently arrived at the same execution order within each tick.

### Take → Clear → Make

These three phases run **in strict priority order** per product per tick.

**Phase 1 — Take**

Before quoting anything, scan the order book for orders that are clearly mispriced relative to your fair value estimate. Take them aggressively.

- If another bot is offering below your fair value: buy it immediately.
- If another bot is bidding above your fair value: sell into it immediately.
- This is guaranteed edge. There is no fill uncertainty. Do not skip this.

**Phase 2 — Clear**

If your position is skewed after taking, or was already skewed from prior ticks, execute trades to flatten toward zero before re-quoting.

- These trades may be 0-EV or slightly negative EV. That cost is worth paying because it frees position capacity.
- The correct sizing is: enough to get back within your soft limit, not necessarily all the way to zero.
- Linear Utility documented this adding ~3% to total PnL just from freeing capacity for future profitable trades.

**Phase 3 — Make**

Only after Take and Clear: post passive quotes around fair value.

**Why this order matters**

Mid-ranked teams typically implement only "Make" with reactive inventory management. This means:

1. They leave guaranteed Take alpha on the table every tick — free money from mispriced orders they walk past.
2. Their inventory management is always one step behind. By the time they respond to a skewed position, they've already missed profitable fills.

The three-phase structure solves both problems by construction.

---

## 2. Fair Value Estimation

### Wall Mid vs. Raw Mid

Raw mid-price `(best_bid + best_ask) / 2` is easily distorted by pennying bots — bots that place a tiny order 1 tick inside the spread to manipulate the apparent midpoint. Wall Mid is more robust:

```
wall_mid = (deepest_visible_bid + deepest_visible_ask) / 2
```

Where "deepest visible" means the outermost price level in the order book with meaningful volume, not just the best bid/ask. This filters noise from single-lot pennying.

Use Wall Mid as the base input for every downstream signal.

### Bot-Filtering for Slow Random Walk Products

For products with no fixed true value (Starfruit, Kelp, Tomatoes), raw mid is even more dangerous because slow-moving bots with stale quotes bias the apparent price.

Linear Utility identified a single consistent market-maker bot posting uniform order sizes and tracked only that bot's mid. This is a cleaner fair value signal than the composite market mid.

Alternative: volume-weighted mid (VWAP of the best bid/ask) is more stable than equal-weighting. The Rank-13 P2 team used this successfully.

### Ornstein-Uhlenbeck for Mean-Reverting Products

For products that lack a fixed anchor but exhibit mean-reversion (identifiable via the drift SNR profiler: `tools/profile_product.py`), model the price as an O-U process:

```
dX = θ(μ - X)dt + σ dW
```

Fit the mean-reversion speed θ, long-term mean μ, and volatility σ from the training data. Use this model to derive fair value at each tick rather than using a raw moving average.

Frankfurt Hedgehogs and AlphaBaguette both modeled Kelp this way in P3.

### Regression Warning

Never regress in price space. Prices are near-collinear across time; you will always get R² > 0.95, all of it spurious. Regress on price changes (returns), normalized spreads, or deviations from fair value.

---

## 3. Olivia — The Highest-Value Single Alpha Source

Olivia is an IMC NPC bot present in every Prosperity round. She has one consistent behavior: **buy at daily lows, sell at daily highs**, across multiple products. Confirmed products include Squid Ink, Croissants, Kelp, and variants (Ukulele, Roses) depending on the year. She trades in approximately 15-lot sizes.

### Detection Before Round 5 (No Trader IDs)

Track the running daily high and running daily low. When a market trade occurs at a new daily low with a lot size consistent with ~15 units, Olivia is buying. When a market trade occurs at a new daily high with ~15 units, Olivia is selling.

Frankfurt Hedgehogs' false positive rate: approximately 15%. Adjust for this with a confidence filter (e.g., require two consecutive signals before acting, or size down on first signal).

```python
if trade.price <= daily_low and trade.quantity >= 14:
    daily_low = trade.price
    olivia_signal = "BUY"
elif trade.price >= daily_high and trade.quantity >= 14:
    daily_high = trade.price
    olivia_signal = "SELL"
```

### Detection After Round 5 (Trader IDs Visible)

From Round 5 onward, `market_trades` entries contain counterparty trader IDs. Observe directly:

```python
for trade in market_trades:
    if trade.buyer == "Olivia":
        olivia_signal = "BUY"
    elif trade.seller == "Olivia":
        olivia_signal = "SELL"
```

Frankfurt Hedgehogs: "switching to direct ID observation eliminated false positives while reducing parameter-optimization complexity." Throw out the extrema filter the moment IDs are visible.

### How to Trade the Signal

When Olivia's signal fires, take maximum directional exposure in the same direction, as aggressively as the position limit allows. The signal tends to persist intraday.

- Frankfurt Hedgehogs: approximately 8,000 SeaShells per product per round from Olivia detection alone.
- CMU team: "YOLOed Croissants following Olivia's signal," achieving 120k+ SeaShells on best days vs. 50k from pure statistical arbitrage.
- Multiple teams: "going all-in when Olivia's signal fires produced the best results."

Secondary use: Olivia's net Croissants direction biases Picnic Basket arb thresholds. If she's net long Croissants, shift your basket long entry threshold lower (more willing to go long the basket). Frankfurt Hedgehogs implemented this as `ETF_THR_INFORMED_ADJS`, an adjustment array indexed by inferred Olivia position.

---

## 4. Bot Exploitation as Alpha

Top teams treat the market as having identifiable, exploitable participants. Mid-ranked teams treat all participants as random or rational.

### Identifying Bots

Signals that a participant is a programmatic bot:
- Uniform order sizes appearing repeatedly (same lot size every time)
- Activity at consistent price relationships (always 1 tick inside spread, always at daily extrema)
- Activity at consistent timestamp patterns (same timestep offsets from market open)

Once identified, characterize the bot's strategy fully. Trade against it.

### Known Bot Patterns

**The Smart Taker (Macarons / conversion products)**

Frankfurt Hedgehogs identified a hidden aggressive buyer in the Macarons local market that accepts limit sell orders at exactly `int(externalBid + 0.5)`. Quote your sell at this price. The taker fills you reliably without you needing to cross the spread.

Result: captures ~60% of theoretical maximum arbitrage profit, compared to ~30% from naive two-sided arbitrage. No guesswork about fill probability.

**The Orchids Massive Taker (Prosperity 2)**

Linear Utility discovered a single aggressive buyer in the Orchids local market creating a persistent one-sided arbitrage. They adapted their edge algorithm dynamically to extract 573,000 SeaShells. This was their entire margin of victory at 2nd global. The strategy leaked to Discord mid-competition; they dropped from 3rd to 17th.

Lesson: when you find a bot-based edge, do not share it publicly.

**Bots from Prior Years**

Multiple teams (Linear Utility P2, multiple P3 teams) found that bot behavioral timing was consistent across competition years. Even when IMC regenerated price paths, the same bots placed orders at similar timestep offsets.

Check: download prior years' data and correlate market trade timestamps (not prices) across years. If specific timesteps show consistent trading activity, a bot is likely active there again.

---

## 5. Basket and ETF Arbitrage

### Core Principle: Trade Only the Basket

Never attempt to arbitrage by simultaneously trading the basket and all its components. The position limits on each component interact: your component position capacity is consumed by the hedge, leaving no room for the basket's own limit to be fully utilized. The math does not work.

The correct approach: trade only in the basket instrument. Use the synthetic value (weighted sum of component fair values) as a signal to determine entry direction and size. Execute only basket orders.

### Entry Thresholds: Fixed Beats Dynamic

Frankfurt Hedgehogs explicitly tested fixed entry thresholds versus dynamic z-scores on Picnic Baskets and found fixed thresholds more robust.

Dynamic z-scores introduce a second optimization surface (the lookback window for the z-score normalization). With 3 days of training data, this second surface overfits. Fixed thresholds have only one parameter.

### Optimal Hedge Ratio: Half

Frankfurt Hedgehogs formally derived that the optimal hedge ratio is 50%, not 100%. The intuition: fully hedged arbitrage lowers variance but also lowers expected value because you pay spread cost on every component leg. Unhedged basket-only trading has higher variance but higher expected value. The empirical optimum (across multiple products and years) is 50% — trade half your basket position in the legs.

CMU team used "100% of Basket 1 limits, 60% of Basket 2 limits" for their two-basket products, derived via PnL optimization.

### Exit at Zero Crossing

Exit when the spread between basket market price and synthetic fair value crosses zero — not when it reaches a symmetric entry threshold in the opposite direction. Waiting for full reversion introduces delta risk: the spread may reverse again before completing its reversion.

---

## 6. Conversion and Arbitrage Products

### Immediate Checks When a Conversion Product Appears

Run these checks in the first 50 timesteps:

```
import_arb = local_bid > external_ask + import_tariff + shipping
export_arb = external_bid - export_tariff - shipping > local_ask
negative_tariff = import_tariff < 0  # free money: always convert
```

If `negative_tariff` is true, execute conversion at the maximum allowed rate every tick without further analysis.

### The Smart Taker Pattern

Before building a full two-sided arbitrage, test: does quoting a sell limit at `int(externalBid + 0.5)` consistently receive fills? If yes, a smart taker bot is present. Use this as your primary execution strategy rather than crossing the spread yourself. It is more reliable and avoids paying the spread.

### Storage Costs are a Hard Constraint

Holding a long conversion position accrues storage costs per tick. Model these explicitly before entering:

```
breakeven_hold_ticks = spread_captured / storage_cost_per_tick
```

If you cannot convert or unwind the position within this window, do not enter. Multiple teams ended rounds with large Macarons/Orchids inventories where storage erased all spread profit.

### Conversion Limit Per Tick

Conversion is typically limited to 10 units per timestep. Never assume you can convert a large accumulated position quickly.

---

## 7. Options and Vouchers

### The Volatility Smile is Non-Negotiable

Implied volatility is not constant across strikes. Different strikes on the same underlying have different IVs — this is the volatility smile. A flat-vol assumption produces systematically wrong prices for all non-ATM strikes.

Fit a quadratic smile:

```python
# m = moneyness normalized by sqrt(time_remaining)
m = math.log(strike / spot) / math.sqrt(time_remaining)
iv_fair = a * m**2 + b * m + c
```

Fit `a, b, c` from the implied vols across all visible strikes. Use `iv_fair(m)` as the theoretical IV for any strike, then compute its theoretical price via Black-Scholes.

Alpha Animals attempted to use rolling IV averages without the smile adjustment. Their model failed on submission day. The smile is critical.

### Python-Safe Black-Scholes

No scipy or numpy. Use the Abramowitz-Stegun approximation for the normal CDF (max error 1.5e-7):

```python
def norm_cdf(x):
    t = 1.0 / (1.0 + 0.2316419 * abs(x))
    poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))))
    pdf = math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)
    cdf = 1.0 - pdf * poly
    return cdf if x >= 0 else 1.0 - cdf

def black_scholes_call(S, K, T, sigma, r=0.0):
    if T <= 0 or sigma <= 0:
        return max(S - K, 0.0)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
```

### Delta Hedging Trade-off

| Hedge ratio | Effect |
|---|---|
| 100% | Lowest variance, lowest EV (pays full spread on hedge every rebalance) |
| 50% | Empirical optimum in multiple top teams' testing |
| 0% | Highest EV if directional bias is small; highest variance |

CMU team: "paying 40k/day in hedging costs eliminated the profit from gamma scalping." They moved to 0% hedge for better net EV. Frankfurt Hedgehogs settled on 50%.

Start at 50% and adjust based on official results.

### IV Deviation Triggers

Frankfurt Hedgehogs' approach:
- Compute `switch_means` = average deviation of all strikes' market IV from their smile-fair IV.
- If `switch_means > 0.7`: enter IV scalp positions (buy cheap IV, sell rich IV strikes).
- Track mean-reversion on the underlying separately (EMA deviation + theo-diff > 5 ticks).
- These two are independent alpha sources — size them separately.

### Cross-Voucher Arbitrage

If voucher A is below its smile-fair price and voucher B is above its smile-fair price:
- Buy voucher A, sell voucher B.
- Delta of the two options partially cancels (near-zero net delta for near-equal moneyness).
- The spread position profits when the market corrects the IV mismatch.

This is lower-risk than single-voucher directional trades.

---

## 8. Overfitting Prevention

### The Landscape Stability Criterion

Frankfurt Hedgehogs explicitly defined their parameter selection rule: **prefer flat plateaus over sharp peaks**.

For any parameter you are tuning, plot PnL as a function of that parameter value across its feasible range. Accept only parameters where performance is stable across ±20% of the chosen value.

A strategy earning 15k/day stably is preferable to one earning 20k/day at the optimum and 5k/day everywhere else. Prosperity training data is too limited (3 days) to trust a sharp peak.

Implementation:

1. Run a parameter grid with fine resolution.
2. Identify all values with PnL within 10% of the peak.
3. Choose the center of that range, not the peak.

### Out-of-Sample Validation

With 3 training days, use 2 for fitting and 1 for validation. Never tune parameters to maximize performance on all 3 days simultaneously.

### Monte Carlo for Robustness

chrispyroberts (7th global, P3) built a Rust Monte Carlo backtester that generates 1,000 synthetic market sessions from a calibrated generative model. This enables testing against a distribution of scenarios rather than just 3 historical days.

For Python: generate synthetic price paths from a fitted O-U or GBM model, perturbing the parameters within their uncertainty bounds. Run your strategy on 100+ synthetic days and report the 25th-percentile PnL. A strategy that does well in the 25th percentile is more robust than one that maximizes the median.

### Never Optimize for Website Score

The official website sim has randomness (bot behavior, fill timing) that is not present in historical data. Hill-climbing the website score means overfitting to that noise. Use local backtesting for parameter tuning and the website only for final validation.

### CMA-ES Specific Warning

CMA-ES will find parameters that exploit sim artefacts (ghost fills, step count differences) as easily as genuine edge. Treat any CMA-ES result that shows large improvement as suspect until confirmed by multiple official submissions:

- If a penalty parameter (markout threshold, damping factor) moves dramatically → suspicion level: high.
- If the parameter controls a protective mechanism (stop-quoting condition) and moves toward "never trigger" → likely exploiting sim artefacts.
- Require first-principles explanation before accepting a CMA-ES change.

---

## 9. Cross-Year Data

### The Linear Utility Discovery

Linear Utility (2nd global, P2) found that Prosperity 2023 and 2024 price paths for Coconuts and Roses correlated at R² = 0.99. They pre-computed the optimal trade sequence given the predicted price path, using dynamic programming, then executed it live. This single technique was responsible for 2.1 million SeaShells — their entire margin of victory.

### Current Status

IMC became aware of this and deliberately regenerated price paths for P3. Direct price path reuse is less reliable now.

However, **bot behavioral timing may still be consistent even if price levels change.** Bots are likely programmed with the same timestep logic in P4 as in P3. The specific timestep at which a bot places orders (not the price it places them at) may be stable.

### How to Check

1. Download all prior years' data.
2. For each product, compute the distribution of timestamps at which unusual market trades occur (large size, new daily extrema, etc.).
3. Test whether these timestamp patterns appear at the same offsets in the current year's data.

If a pattern is found: hard-code extra buy/sell orders at those timesteps to front-run the known bot.

---

## 10. Code Architecture and Robustness

### State Serialization — The Most Dangerous Bug

All rolling window state, EMA values, Olivia detection state, daily high/low trackers, and position histories must be serialized to `traderData` as a JSON string at the end of every tick. Deserialize at the start of the next tick.

Class variables reset when a submission reloads. This is not a hypothetical risk — CMU team dropped from 3rd to 241st in one round because their rolling window state reset.

```python
def run(self, state: TradingState):
    mem = json.loads(state.traderData) if state.traderData else {}

    ema = mem.get("PRODUCT_EMA", initial_value)
    daily_low = mem.get("OLIVIA_DAILY_LOW", float("inf"))

    # ... all trading logic ...

    mem["PRODUCT_EMA"] = ema
    mem["OLIVIA_DAILY_LOW"] = daily_low
    return result, conversions, json.dumps(mem)
```

### Rolling Windows: deque, Not List

`list.pop(0)` is O(n). With multiple products and 1,000 timesteps per day, a list-based rolling window of length 200 will cause performance degradation. Use:

```python
from collections import deque
window = deque(maxlen=200)
window.append(new_value)   # automatically pops oldest when full
```

### Logger Truncation

IMC truncates stdout at approximately 3,750 characters per tick. If you use the default Prosperity logger that prints full state, you will overflow this limit and lose log data.

Use the compact single-line logger format from the Prosperity 3 visualizer. It encodes state, orders, and traderData into a single compressed line per tick.

### Module Isolation

Each product's trading logic must be wrapped in a try/except:

```python
try:
    orders_A = module_A.build_orders(state, memory)
except Exception:
    orders_A = []
```

A division by zero, a bad traderData deserialization, or an initialization bug in one product module must not prevent other modules from running.

### Available Imports

IMC explicitly permits: `pandas`, `numpy`, `statistics`, `math`, `typing`, `jsonpickle`, plus the full Python 3.12 standard library. **SciPy is not listed and should be assumed unavailable.**

Practical implication:
- `numpy` arrays, `numpy.linalg`, etc. are fine to use
- `scipy.stats.norm.cdf` is NOT available — use the Abramowitz-Stegun approximation in Section 7, or `numpy`-based alternatives
- Rolling statistics can use `collections.deque` (stdlib) or numpy arrays — deque is simpler for most cases

---

## 11. Common Mistakes in Mid-Ranked Teams

From explicit callouts across multiple write-ups:

**Structural**
- Only implementing Make, no Take step — missing guaranteed free edge every tick.
- Reactive inventory management instead of proactive Clear phase.
- Not accounting for storage costs in conversion products — inventory bleeds.

**Overfitting**
- Grid-searching and picking the peak parameter value.
- Optimizing for website score.
- Using sunlight, humidity, or multi-feature regressions without structural justification — every team that tried this lost to teams that used simpler, structurally-grounded signals.
- Linear regression in price space (R² will be 0.95+ spuriously).

**Technical**
- State stored in class variables — resets on reload.
- `list.pop(0)` for rolling windows — O(n) performance.
- Importing scipy or numpy — not available in IMC's environment.
- Single-product testing only — combined backtest with all active products reveals position limit conflicts and memory key collisions.

**Operational**
- Sharing a discovered edge publicly during the competition — it will be replicated immediately.
- Not switching Olivia detection to direct trader ID observation once IDs become available in Round 5.

---

## 12. Priority Checklist for Each New Round

When a new round opens, run these checks in order before writing any product-specific code:

1. **Profile the data**: `python3 tools/profile_product.py data/prices_round_N_day_-1.csv`
   - Get drift SNR → archetype classification
   - Get spread, volume, autocorrelation
2. **Identify product type**: fixed-value, slow random walk, mean-reverting, trending drift, ETF basket, options, conversion product?
3. **Check for Olivia**: does the new product show the daily-extrema pattern in the first 200 timestamps?
4. **Check for conversion arbitrage**: run the import/export bounds check immediately.
5. **Check for cross-year bot timing**: compare this product's market trade timestamps to the same product in prior years.
6. **Submit existing bot first**: the current working bot with the new product safely ignored is better than a broken bot that crashes on the new product.
7. **Stage complexity**: simple implementation → official result → diagnose → targeted fix → optimize last.

---

## 13. Book Health and Median-Guard Fair Value

When the visible order book becomes unreliable — thin, one-sided, or with an abnormally wide spread — blindly trusting the computed fair value produces dangerous orders. This section describes how to detect and respond to degraded book states.

### What degrades book health

- Only one side has orders (no bid or no ask visible)
- Spread is more than 3× the product's historical average
- Top-of-book depth is less than 2 lots on either side
- Fair value has moved more than N ticks in one step with no trade confirming it (likely a pennying bot pulling an order)

These conditions can appear temporarily (a bot withdrawing its quote for one tick) or persistently (a product with genuinely thin markets). The response should be proportional.

### Book health score (practical lightweight version)

```python
def book_health(od, hist_spread_mean, max_guard_spread_mult=3.0):
    bb = best_bid(od)
    ba = best_ask(od)
    if bb is None or ba is None:
        return 0.0          # one-sided: no trust
    spread = ba - bb
    if spread <= 0:
        return 0.0          # crossed book: no trust
    spread_ratio = spread / max(hist_spread_mean, 1.0)
    if spread_ratio > max_guard_spread_mult:
        return 0.0          # spread blow-out: no trust
    bid_vol = od.buy_orders[bb]
    ask_vol = abs(od.sell_orders[ba])
    depth_score = min(1.0, (bid_vol + ask_vol) / 10.0)   # normalise to ~10 lots
    spread_score = max(0.0, 1.0 - (spread_ratio - 1.0) / (max_guard_spread_mult - 1.0))
    return 0.5 * depth_score + 0.5 * spread_score        # 0 = broken, 1 = healthy
```

### Gating execution by health

| Health score | Action |
|---|---|
| ≥ 0.7 | Normal: take mispricings, full passive quotes |
| 0.3 – 0.7 | Guarded: use median-guard fair, reduce size by 50% |
| < 0.3 | Repair only: no aggressive takes, tiny passive quotes to maintain presence |

### Median-guard fair value

When health is below the guard threshold, replace the normal fair with:

```python
guarded_fair = sorted([anchor_fair, stable_mid, last_good_fair])[1]  # median of three
fair = min(normal_fair + max_guard_ticks,
           max(normal_fair - max_guard_ticks, guarded_fair))
```

Where:
- `anchor_fair` = reference price or long-run anchor (e.g. 10,000 for fixed-center products)
- `stable_mid` = `vwap_mid(od)` or `wall_mid(od)` from the current book
- `last_good_fair` = the fair value computed at the last tick where health ≥ 0.7
- `max_guard_ticks` = maximum allowed deviation from normal fair (e.g. 3–5 ticks)

The median of three prevents any single corrupted signal from moving the fair. The clamp further limits the damage to `max_guard_ticks`.

**Crucially: always persist `last_good_fair` in `traderData`.** If it's lost on a tick reset, the guard falls back to the anchor, which is still safe.

### What this protects against

- A pennying bot that pulls its quote for one tick, making your fair jump 5 ticks, triggering a large aggressive order at the wrong price
- A thin book after a large sweep where only stale far-away quotes remain
- Any tick where your fair value computation returns a clearly wrong number due to degenerate input

---

## 14. Terminal Inventory Pressure

For any product that is **not** a deterministic carry/drift product (i.e. you do not *want* to hold a large position at session end), inventory left at the end of the session is pure risk. The official exchange closes, positions carry over to the next round with a different regime, and you cannot manage them.

The correct approach is a session-progress schedule that increases flattening pressure as the session nears its end. This is distinct from normal inventory skew — it is a hard escalation that overrides passive quoting.

### Session progress

```python
progress = state.timestamp / MAX_TIMESTAMP   # 0.0 at open, 1.0 at close
```

`MAX_TIMESTAMP` for Prosperity: 999,900 on historical data (10,000 steps × 100). Confirm from the data before hardcoding.

### The three pressure stages

**Stage 1 — mild pressure (progress ≥ 0.70)**

Tighten inventory skew. Quote normally on the flattening side, widen quotes on the accumulating side.

```python
if progress >= 0.70 and abs(position) > soft_limit * 0.5:
    # skew quotes more aggressively toward zero
    inventory_skew_multiplier = 1.5
```

**Stage 2 — strong pressure (progress ≥ 0.85)**

Stop adding to inventory. Only quote on the side that reduces position. Reduce passive quote size on the accumulating side to near-zero.

```python
if progress >= 0.85:
    if position > 0:
        mgr.buy(...)    # suppress entirely
        # only sell quotes remain
    elif position < 0:
        mgr.sell(...)   # suppress entirely
        # only buy quotes remain
```

**Stage 3 — emergency flatten (progress ≥ 0.95)**

Accept worse prices to get flat. Take aggressively at small edge. Suspend all passive quoting.

```python
if progress >= 0.95 and abs(position) > 0:
    # take to reduce — accept lower edge threshold
    if position > 0 and book.best_bid > fair - emergency_take_edge:
        mgr.sell(book.best_bid, abs(position))
    elif position < 0 and book.best_ask < fair + emergency_take_edge:
        mgr.buy(book.best_ask, abs(position))
```

### Exception: carry and drift products

Do **not** apply terminal pressure to products like IPR where the edge comes from holding a directional position through the session. Applying flattening pressure at 95% of the session directly destroys the carry PnL you spent the entire session accumulating.

Gate the pressure schedule by product archetype. Only activate for market-making products, not carry products.

### Why this matters

Without terminal pressure, a market-making bot will accumulate inventory near session end (because the passive fill rate continues but the reverting fills decrease as the day ends), then carry that inventory into the next round at a different price. This is a consistent, avoidable loss.

---

## 15. Plateau Classification — Diagnosing Flat PnL Regions

After each official submission, plot the cumulative PnL trajectory by product. Flat regions — where PnL is not growing — are the primary diagnostic signal. There are five distinct causes, each requiring a different fix. Applying the wrong fix wastes a submission slot.

### The five plateau types

**Type A — Correct no-trade**

The bot correctly detected a dangerous book or adverse regime and stopped quoting. PnL is flat because trading is paused, not because you are missing fills.

Identifying markers:
- Health score or toxicity flag was high during the flat region
- No fills on either side during the flat region
- Book was thin or one-sided when you inspect the raw log

Fix: **none**. This is the defensive mechanism working correctly. If anything, verify the health/toxicity trigger is not too aggressive — if the flat region is very long, the threshold may be too conservative.

---

**Type B — Missed opportunity**

The book was healthy and the signal was valid, but you got no fills. The price moved without you participating.

Identifying markers:
- Book health was high during the flat region
- No fills despite visible quotes
- Other market participants were trading (market trades visible in the log)

Cause: your passive quotes are priced too far from the market, or you lost queue priority.

Fix: **side-specific reentry**. Track `ticks_since_last_buy_fill` and `ticks_since_last_sell_fill` separately. If a side is starved beyond a threshold and health is high, improve that side's quote by 1 tick.

```python
if ticks_since_buy_fill > STARVATION_THRESHOLD and health >= 0.7:
    buy_edge -= 1.0   # move bid 1 tick closer to fair
```

Do not do this on both sides simultaneously — you would narrow the spread without any evidence the other side is also starved.

---

**Type C — Inventory blocked**

The bot is at or near its position limit and cannot take profitable fills in the preferred direction.

Identifying markers:
- Position is near soft or hard limit during the flat region
- Fills are one-sided (only selling, never buying, or vice versa)
- Profitable takes are visible but not taken (edge is positive but position cap is hit)

Fix: **earlier inventory recycler**. The Clear phase (Take → Clear → Make) should trigger earlier — reduce the `CLEAR_BUFFER` threshold or lower `SOFT_LIMIT` to leave more capacity available. Also check whether the `CLEAR_EDGE_LIMIT` is too conservative (requiring too much edge before recycling).

---

**Type D — Stale toxicity**

The book recovered to a healthy state, but an earlier toxic fill or bad markout event locked the bot into a defensive posture. The bot is refusing fills that are now safe.

Identifying markers:
- Markout EMA or toxicity flag was elevated from an earlier event
- Book health is now high but quoting is still suppressed
- Flat region starts after a brief spike of bad fills, then continues even as prices stabilise

Fix: **faster toxicity decay**. Add a reset trigger: if `ticks_since_last_toxic_event > DECAY_WINDOW` and current book imbalance is neutral, reduce the markout penalty by 50% immediately rather than waiting for the slow EMA to decay.

```python
if ticks_since_toxic > DECAY_WINDOW and abs(book_imbalance) < 0.15:
    buy_markout_ema *= 0.5
    sell_markout_ema *= 0.5
```

---

**Type E — Signal neutral / no structural edge**

The product genuinely has no edge available at this time. Spread is too narrow to make anything, fair value signals are ambiguous, and the product is effectively random-walking.

Identifying markers:
- Book health is high, no toxicity, no inventory block
- Fills are happening but PnL per fill is near zero
- All signals (imbalance, stable-gap, markout) are near zero simultaneously

Fix: **reduce activity, do not add complexity**. Post tiny two-sided quotes at the minimum size to remain present, but do not try to force edge that does not exist. This is the time to reduce `FRONT_SIZE` and `BACK_SIZE`, not to add new signals. Adding signals to a signal-neutral environment finds noise.

### Quick classification checklist

After each flat region, answer in order:

1. Was health/toxicity high during the flat region? → **Type A**, leave alone
2. Were there profitable market trades I did not participate in? → **Type B**, reentry
3. Was position at or near limit? → **Type C**, recycler earlier
4. Did flat region start after a burst of bad fills, with recovery? → **Type D**, faster decay
5. None of the above, fills exist but zero edge? → **Type E**, reduce activity
