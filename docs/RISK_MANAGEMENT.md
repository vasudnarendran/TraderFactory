# Risk Management

This document covers the core risk management principles that apply to any Prosperity round, regardless of what products are introduced. It is written to be useful before product data is available.

---

## 1. Position Limit Risk

Position limits in Prosperity are **hard constraints enforced at order submission**. An order that would push the position beyond the limit is rejected in full — there is no partial fill. This has non-obvious consequences.

### Track projected position, not current position

Your current physical position is not the right number to check before submitting. You must track:

```
projected = physical_position + sum(pending_passive_orders)
```

Passive orders are in the book but not yet filled. They count against your effective capacity. If you ignore them and submit additional orders, you will hit the limit unexpectedly at the worst moment.

### Reserve capacity before you need it

Never allocate 100% of a position limit to one directional trade. You need headroom for:

- **Responding to adverse fills** — if you get swept long and need to reduce, you must have capacity to add offsetting shorts
- **Hedging** — if a new product is a derivative on an existing product, your delta-hedge demand competes directly with directional trades on that product for the same limit
- **Reversion** — mean-reverting products will pull you to one extreme; you need room to accumulate before the reversion pays off

A position limit of ±N does not mean you should target ±N. A practical ceiling is 70–80% of limit for directional exposure, reserving the remainder for operational headroom.

### Linked products share a constraint budget

When a product is derived from or arbitrage-linked to another product, their position limits are independent but their **operational demands interfere**. If you hold 200 lots of a derivative whose hedge requires 160 lots of the underlying, and the underlying has a ±200 limit, you have consumed 80% of the underlying's limit just for hedging — leaving almost no room for the underlying's own trading logic.

The safest rule: identify all inter-product dependencies at round start, calculate worst-case hedge demand, and set soft limits on each product accordingly before any trading begins.

---

## 2. Inventory Risk

Inventory risk is the core risk of market making. It arises any time you hold a position that was accumulated by passively providing liquidity.

### The two types of passive fill

Not all passive fills are equal:

- **Noise fills** — a liquidity-taking counterparty with no informational edge hits your quote. The price tends to revert toward fair value after the fill. Your inventory is temporary and profitable.
- **Adverse fills** — an informed counterparty takes your liquidity because they know something about near-term price direction. The price continues moving against your position. Your inventory is structural and costly.

The two look identical at fill time. You can only distinguish them by their **markout** — how the price moves in the N steps following the fill.

### Markout as the primary inventory diagnostic

Track an exponential moving average of post-fill price changes:

```
markout_ema = alpha * (price_N_steps_later - fill_price) + (1 - alpha) * markout_ema
```

Interpret the result per side:
- Buy markout consistently negative → your bids are being hit by informed sellers → reduce bid size or pull quotes
- Sell markout consistently negative → your offers are being lifted by informed buyers → reduce ask size

Use this signal to gate order size (soft markout penalty) and to gate quoting entirely (hard markout cutoff). The alpha parameter controls responsiveness vs. noise sensitivity — fast alpha reacts quickly but overreacts to random runs; slow alpha is stable but slow to protect you in a genuine regime shift.

### Inventory skew

When you hold a directional position, adjust both sides of your quote to encourage mean-reversion:

- If long, move both bid and ask **down** to attract sellers and deter buyers
- If short, move both bid and ask **up** to attract buyers and deter sellers

The skew magnitude should be proportional to position size. A nonlinear curve (convex in position) is more appropriate than a linear one: small positions warrant mild skew, large positions warrant aggressive skew, and positions near the hard limit should trigger mode switches (stop quoting the same direction entirely).

### Distinguishing adverse selection from mean-reversion

On mean-reverting assets, a passive fill that looks adverse in the short term may be exactly what you want. The price moves against you briefly, then reverts, and your fill ends up profitable. Applying an aggressive markout-based cutoff to a mean-reverting asset will stop your quoting exactly when quoting is most profitable.

Key question at round start: **is the asset mean-reverting or trending?** The answer changes how aggressively you penalise passive fills that appear "bad."

---

## 3. Adverse Selection and Signal Quality

Adverse selection is the systematic tendency for market prices to move against passive orders after they fill. It is a function of the **information environment** — how much better informed the aggressor is relative to you.

### Book imbalance as a forward signal

The ratio of bid-side volume to ask-side volume at the top of the book is a weak but reliable directional indicator:

- Heavy bid imbalance → more buyers willing to transact at current prices → price likely to rise
- Heavy ask imbalance → more sellers → price likely to fall

Use imbalance to:
1. Skew your fair value estimate (upward on bid imbalance, downward on ask imbalance)
2. Gate which side of the book you actively quote — in heavy bid-imbalance states, quoting the ask is riskier

### Signal agreement and disagreement

When multiple signals (book imbalance, short-term price momentum, long-term anchor) agree on direction, their combined signal is more reliable than any one signal alone. Trade larger in agreement states.

When signals disagree, reduce size. The disagreement itself is information: either the market is transitioning regimes or one signal is stale. In disagreement states, prefer the faster signal (imbalance, micro-price) over the slower one (trend, anchor) for immediate execution decisions.

### Sweep detection

Large aggressive sweeps — single orders that consume multiple levels of the book — signal informed directional conviction. After a sweep:

- The residual book is one-sided for several timestamps
- Price often continues in the sweep direction
- Passive orders placed in the sweep direction are likely to get adversely filled

After detecting a sweep, pause or reduce quoting in the swept direction for a brief window. Resume when the book refills.

---

## 4. Cross-Product Portfolio Risk

Once multiple products are active simultaneously, each product's module interacts with the others through shared capital, shared position capacity (for linked products), and shared code path.

### Module isolation

Each product's trading logic should be defensively contained. A bug, division by zero, or runaway position in one module should not prevent other modules from running. The structure:

```python
try:
    orders_A = module_A.build_orders(state, memory)
except Exception:
    orders_A = []   # fail silent, emit nothing

try:
    orders_B = module_B.build_orders(state, memory)
except Exception:
    orders_B = []
```

A crash in the options module should not silence the market-making module.

### Test all modules together

The most common failure mode when a new product is introduced: the new module is tested in isolation, but the combined backtest reveals a position conflict (new product's hedge demand consumes an existing product's capacity), a memory key collision, or a total position exposure that is far higher than intended.

Run a combined backtest of all active products before each submission. Review total SeaShell exposure across all positions. A single bad module can dwarf the PnL of all correctly functioning modules.

### Correlation and joint exposure

If two products are positively correlated (both decline in risk-off states, for example), a long position in both compounds your directional risk even if each position is within its own limit. Conversely, negatively correlated products can serve as natural hedges.

At round start, test: do the new products move together with existing products? If so, the combined max-long scenario is worse than either product's individual worst case.

---

## 5. Model Risk

Model risk is the risk that your fair value estimate is systematically wrong.

### Overfitting to limited data

Each Prosperity round provides only 2–3 days of training data. CMA-ES or other optimisers that maximise performance on this data can easily find parameters that exploit artefacts of those specific days rather than genuine structural signals. The result: excellent sim performance, poor official performance.

Symptoms of overfitting:
- A parameter changes dramatically from its prior value without a clear structural reason
- Sim score improves but official score does not
- The parameter controls a penalty or threshold (these are most susceptible — they can be set to "never trigger" and improve sim by removing protective logic)

Mitigation:
- Prefer structural changes over parameter tuning when data is limited
- Use conservative (tighter) default parameters and only relax them when you have multiple official days confirming the relaxation is safe
- Treat large CMA-ES parameter changes with suspicion, especially on penalty-controlling params

### Regime change between training and official

The training data may not represent the official evaluation period. Spread, volatility, and trading volume can all differ. A fair value model calibrated to a specific spread regime may behave unexpectedly when the spread changes.

Build regime checks into the bot:
- Detect if current spread is outside the training range and adjust edge parameters accordingly
- Use adaptive signals (EMAs, rolling estimates) rather than constants wherever possible
- Monitor per-step PnL trajectory in official logs — a consistent downward trend in a specific quartile signals a regime mismatch

### Sim–official gap

The internal sim is a practical approximation, not the official hidden simulator. Known sources of divergence:

- **Passive fill inflation**: the fill model may count trades at prices below your bid as fills even when those trades filled other participants at lower levels. This inflates passive fill counts in sim, making passive-heavy strategies look better than they are.
- **FIFO priority**: on the official exchange, earlier orders at the same price have priority. The sim does not replicate this.
- **Step count**: training data may have 10× more rows than the official evaluation day. Always check this calibration before interpreting sim PnL.

The practical implication: passive fill improvements that show large sim gains should be assumed to be partially sim artefacts until confirmed by multiple official submissions. Aggressive fill improvements (takes) are more reliable in sim because they always execute against visible book levels.

---

## 6. Execution Risk

Orders are processed on each timestamp after a one-step observation delay. You see the market state at step N and submit orders, which execute at step N+1 against whatever the book shows then. The book can move between observation and execution.

### Aggressive vs. passive trade-off

| | Aggressive (take) | Passive (quote) |
|---|---|---|
| Fill certainty | Guaranteed | Uncertain |
| Fill price | At current ask/bid | Better (inside spread) |
| Cost | Pays full spread | Earns partial spread |
| Best use | Must-fill (closing risk, hedging) | Opportunistic (edge capture) |

Never take aggressively when a passive quote at the same price would achieve the same expected fill — the difference is the full spread, which is real cost.

### Order sizing and book depth

When the book is thin (small volume at best bid/ask), a large aggressive order will sweep through multiple levels, paying worse and worse prices. Always size aggressive orders against visible book volume:

```
qty = min(desired_qty, book.best_bid_vol)  # for aggressive sell
```

For passive orders, sizing can be more generous since you only fill what the market brings to you. However, very large passive orders can signal your intent to informed counterparties if the book is public.

---

## 7. Settlement and Expiry Risk

If any product has a defined settlement event — an end-of-round price fix, an option expiry, a contract maturity — the risk profile changes sharply as settlement approaches.

### Near-expiry behaviour

Far from settlement: the product's value is driven by expectation, volatility, and the full remaining time for price to move.

Near settlement: the product converges to intrinsic value. For linear products (futures, forwards), this is the current price. For non-linear products (options), this creates a binary: the product is either worth something (ITM) or nothing (OTM), with the boundary at the strike.

Near expiry, positions that seemed manageable at full time-to-expiry become urgent:
- **Long OTM positions** lose value rapidly and become near-worthless — do not hold to expiry expecting a miracle
- **Short ITM positions** have nearly certain losses at settlement — close or hedge aggressively
- **Theta decay** (time value erosion) is largest for at-the-money positions in the final days — monitor daily time decay cost against expected edge

### Settlement price risk

The settlement price is the official closing price of the underlying at the settlement timestamp. If you are holding a position that settles against this price, you are exposed to a single price fixing event. Liquidity near settlement may be thin and the price may gap against you. Do not assume you can trade out of a large position in the final timestamps.

### Carry-over positions

In Prosperity, positions carry over between rounds. A position taken in Round 3 is still held when Round 4 opens. If the position's risk profile changes materially between rounds (e.g., time-to-expiry decreases, volatility regime shifts), the position that was manageable in Round 3 may be dangerous in Round 4.

At the end of each round, review all open positions and their carry-over risk before the next round opens.

---

## 8. Conversion and Arbitrage Mechanics

Some products have explicit conversion mechanics — the ability to transform one product into another (or into SeaShells) at a defined rate, possibly with a fee.

### Conversion fair value

The theoretical fair value of a convertible product is bounded by:

```
fair_value = reference_product_fair_value ± conversion_cost
```

If the conversion is cheaper in one direction than the other, there is an asymmetric arbitrage band:

```
lower_bound = reference_fair - import_cost
upper_bound = reference_fair + export_cost
```

Trading within this band is not arb-free — conversion is expensive. Trading outside the band is arbitrage.

### Never assume zero-cost conversion

A common mistake is implementing a conversion strategy with the conversion cost hardcoded as zero during initial development, then forgetting to add the cost before submission. The result is a strategy that trades both legs of an apparent arbitrage that does not actually exist, losing the conversion fee on every round trip.

Always model conversion costs explicitly from the first implementation. Treat the cost as a parameter that may be updated when the round brief provides exact numbers.

### Storage and holding costs

Some Prosperity products have explicit storage costs or holding fees per timestamp. These are economically equivalent to a negative carry — holding the position passively costs SeaShells. These costs change the break-even on any position and must be subtracted from the expected PnL before deciding to hold.

---

## 9. Tail Risk and Defensive Mechanisms

The bot runs autonomously. If a bug creates a runaway position, there is no manual intervention. Defensive mechanisms must be built into the bot itself.

### Soft and hard position ceilings in code

Set internal position ceilings below the exchange limit:

```python
SOFT_LIMIT = 0.75 * EXCHANGE_LIMIT   # trigger inventory skew / reduced quoting
HARD_LIMIT = 0.90 * EXCHANGE_LIMIT   # stop quoting same direction entirely
```

The exchange limit is a last resort enforced by rejection. Your internal hard limit is the line you never want to cross under normal operation. The soft limit is the signal to begin active reduction.

### Circuit breakers

If the position has been above the hard limit for N consecutive steps with no successful reduction, switch to emergency flatten mode:

- Stop all passive quoting
- Submit aggressive orders to reduce position toward zero
- Remain in flatten mode until position is within the soft limit

### Sanity checks on fair value

Before computing any order, validate that your fair value estimate is reasonable:

```python
if not (REFERENCE_PRICE * 0.80 < fair_value < REFERENCE_PRICE * 1.20):
    return []   # fair value has blown up; emit nothing
```

A division by zero, a stale anchor, or an initialisation bug can produce a fair value of 0 or infinity. All subsequent order prices will be wrong, and you will submit market orders at catastrophically bad prices.

### Memory state corruption

The bot persists state across timestamps via the `trader_data` memory field. If this state is corrupted (wrong type, missing key, value from a previous day's regime), every subsequent step may behave incorrectly. Always validate state on read:

```python
state = memory.get("PRODUCT_STATE", {})
if not isinstance(state, dict):
    state = {}   # reset rather than crash
```

---

## 10. Rapid Adaptation to a New Round

When a new round opens, you have limited time before first submission. The failure mode is attempting to over-engineer the first submission and introducing bugs, losing the first official day to a broken bot.

### Intake checklist for a new product

1. **Position limit** — what is it? Does it interact with any existing product's limit?
2. **Settlement** — does this product settle? When? Against what price?
3. **Conversion** — can this product be converted to or from another? At what cost?
4. **Archetype** — mean-reverting, trending, basket, derivative, conversion product, or something new?
5. **Fair value sources** — what determines fair value? Book, underlying price, formula, or schedule?
6. **Risk character** — is the risk primarily inventory risk, model risk, settlement risk, or something else?

### Stage the complexity

Do not attempt a fully parameterised, CMA-ES-tunable, multi-signal architecture on day one of a new product. The correct sequence:

1. **Simple submission first** — a minimal implementation with hard-coded conservative parameters that does not crash. Gets official data.
2. **Diagnose first official result** — look at PnL trajectory, fill rates, position behaviour. Identify what is wrong.
3. **Targeted improvement** — fix the highest-impact problem identified. One change per submission where possible.
4. **Optimise last** — only run CMA-ES or heavy parameter tuning after the structural logic is confirmed correct on official data.

The cost of a bad first submission is one official day of data. The cost of a complex first submission with a bug is the same one day, plus the debugging time, plus the risk that the bug produced a large loss that cannot be recovered.
