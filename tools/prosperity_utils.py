"""
prosperity_utils.py — Product-agnostic utilities for IMC Prosperity trader bots.

HOW TO USE:
  Copy the functions/classes you need directly into your single-file bot submission.
  Do not import this file at submission time — IMC only accepts one .py file.

VERIFIED AGAINST:
  - trader_factory/core/datamodel.py (OrderDepth, Order, Trade field definitions)
  - trader_v15.py Book and Manager classes (confirmed data model assumptions)
  - IMC permitted imports: pandas, numpy, statistics, math, typing, jsonpickle,
    and the full Python 3.12 stdlib. SciPy is NOT listed and should be assumed
    unavailable — use norm_cdf() from this file instead of scipy.stats.norm.cdf.

DATAMODEL NOTES (important for correctness):
  - OrderDepth.buy_orders:  Dict[int, int]  — price → volume (volumes POSITIVE)
  - OrderDepth.sell_orders: Dict[int, int]  — price → volume (volumes NEGATIVE)
  - Trade.quantity: always positive (absolute size, direction inferred from buyer/seller)
  - Order(symbol, price, quantity): positive quantity = buy, negative = sell
"""
from __future__ import annotations

import json
import math
from collections import deque
from typing import Dict, List, Optional, Tuple

try:
    from datamodel import Order, OrderDepth, Trade, TradingState
except ModuleNotFoundError:
    from trader_factory.core.datamodel import Order, OrderDepth, Trade, TradingState


# ---------------------------------------------------------------------------
# Book utilities
# ---------------------------------------------------------------------------

def best_bid(od: OrderDepth) -> Optional[int]:
    """Highest bid price in the book. None if no bids."""
    return max(od.buy_orders.keys()) if od.buy_orders else None


def best_ask(od: OrderDepth) -> Optional[int]:
    """Lowest ask price in the book. None if no asks."""
    return min(od.sell_orders.keys()) if od.sell_orders else None


def raw_mid(od: OrderDepth) -> Optional[float]:
    """Simple (best_bid + best_ask) / 2. Returns None if book is one-sided or crossed."""
    bb = best_bid(od)
    ba = best_ask(od)
    if bb is None or ba is None:
        return None
    if bb >= ba:
        return None  # crossed book — do not use
    return (bb + ba) / 2.0


def vwap_mid(od: OrderDepth, levels: int = 3) -> Optional[float]:
    """
    Volume-weighted mid using top N bid and ask levels.
    More stable than raw_mid when multiple levels are present.
    Falls back to raw_mid if book is one-sided.
    """
    if not od.buy_orders or not od.sell_orders:
        return raw_mid(od)
    bid_levels = sorted(od.buy_orders.items(), reverse=True)[:levels]
    ask_levels = sorted(od.sell_orders.items())[:levels]  # ascending by price
    bid_vol = sum(v for _, v in bid_levels)
    ask_vol = sum(abs(v) for _, v in ask_levels)  # sell_orders vols are negative
    if bid_vol <= 0 or ask_vol <= 0:
        return raw_mid(od)
    vwap_bid = sum(p * v for p, v in bid_levels) / bid_vol
    vwap_ask = sum(p * abs(v) for p, v in ask_levels) / ask_vol
    mid = (vwap_bid + vwap_ask) / 2.0
    if vwap_bid >= vwap_ask:
        return raw_mid(od)  # degenerate — fall back
    return mid


def wall_mid(od: OrderDepth) -> Optional[float]:
    """
    Wall mid as implemented by Frankfurt Hedgehogs (2nd global, P3):
        wall_mid = (min(buy_orders.keys()) + max(sell_orders.keys())) / 2

    Uses the OUTERMOST visible bid and ask levels — the lowest bid price and the
    highest ask price in the book. This is the most stable mid possible: pennying
    bots that post single lots just inside the spread have zero effect on it.

    Verified directly from FrankfurtHedgehogs_polished.py get_walls() method.

    Trade-off: can be far from the true transaction price if the book is deep.
    Use as a slow anchor / regime reference, not a tick-level fair value.
    """
    if not od.buy_orders or not od.sell_orders:
        return raw_mid(od)
    bid_wall = min(od.buy_orders.keys())   # outermost (lowest) bid
    ask_wall = max(od.sell_orders.keys())  # outermost (highest) ask
    if bid_wall >= ask_wall:
        return raw_mid(od)
    return (bid_wall + ask_wall) / 2.0


def thick_mid(od: OrderDepth, levels: int = 3) -> Optional[float]:
    """
    Thick mid: picks the highest-volume bid and ask within the top N price levels,
    then averages them. 'Thick' = where the most liquidity is concentrated.

    Different from wall_mid() — this finds the price level with the largest order,
    not the outermost level. Useful when market makers post large passive orders
    at their preferred prices, creating a visible 'wall' of liquidity.

    Implementation mirrors trader_v15.py Book._stable_mid (verified line 231-233).
    sell_orders volumes are negative in the raw datamodel — handled via sort key.
    """
    if not od.buy_orders or not od.sell_orders:
        return raw_mid(od)
    bid_levels = sorted(od.buy_orders.items(), reverse=True)[:levels]
    ask_levels = sorted(od.sell_orders.items())[:levels]  # lowest asks first

    # Highest-volume bid: volumes positive, maximise volume then price for tie-break
    thick_bid = max(bid_levels, key=lambda x: (x[1], x[0]))[0]

    # Highest-volume ask: volumes negative, so most negative = most volume.
    # Minimise (volume, price) — most negative volume wins, lowest price for tie-break.
    thick_ask = min(ask_levels, key=lambda x: (x[1], x[0]))[0]

    if thick_bid >= thick_ask:
        return raw_mid(od)
    return (thick_bid + thick_ask) / 2.0


def micro_price(od: OrderDepth) -> Optional[float]:
    """
    Volume-weighted mid using only best bid and ask (the 'micro price').
    Tilts toward the side with more volume: if more bid volume than ask, pulls
    the mid upward (bullish pressure signal).

    Formula: (ask_px * bid_vol + bid_px * ask_vol) / (bid_vol + ask_vol)
    Matches trader_v15.py Book.micro (verified line 178-180).
    """
    bb = best_bid(od)
    ba = best_ask(od)
    if bb is None or ba is None or bb >= ba:
        return raw_mid(od)
    bid_vol = od.buy_orders[bb]
    ask_vol = abs(od.sell_orders[ba])
    total = bid_vol + ask_vol
    if total == 0:
        return (bb + ba) / 2.0
    return (ba * bid_vol + bb * ask_vol) / total


def book_imbalance(od: OrderDepth, levels: int = 1) -> float:
    """
    Returns (bid_vol - ask_vol) / (bid_vol + ask_vol) in [-1, 1].
    Positive = more bid volume = upward price pressure.
    At levels=1 matches trader_v15.py Book.imbalance (verified line 181).
    """
    if not od.buy_orders or not od.sell_orders:
        return 0.0
    bid_levels = sorted(od.buy_orders.items(), reverse=True)[:levels]
    ask_levels = sorted(od.sell_orders.items())[:levels]
    bid_vol = sum(v for _, v in bid_levels)
    ask_vol = sum(abs(v) for _, v in ask_levels)
    total = bid_vol + ask_vol
    if total == 0:
        return 0.0
    return (bid_vol - ask_vol) / total


# ---------------------------------------------------------------------------
# EMA
# ---------------------------------------------------------------------------

def ema(prev: Optional[float], current: float, alpha: float) -> float:
    """
    Exponential moving average. alpha is the weight on the NEW value.
    alpha=1.0 → tracks current exactly. alpha→0 → very slow-moving.
    Handles None on first call (returns current as the initialised value).
    Matches trader_v15.py ema() (verified line 121-124).
    """
    if prev is None:
        return current
    return (1.0 - alpha) * prev + alpha * current


# ---------------------------------------------------------------------------
# State serialization
# ---------------------------------------------------------------------------

def load_memory(trader_data: str) -> dict:
    """
    Safe deserialise of traderData JSON. Returns {} on missing, empty, or corrupt input.
    Always use this instead of json.loads(state.traderData) directly.
    Matches trader_v15.py Trader._load_memory (verified lines 1267-1274).
    """
    if not trader_data:
        return {}
    try:
        parsed = json.loads(trader_data)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, ValueError):
        return {}


def dump_memory(memory: dict) -> str:
    """
    Serialise memory dict to compact JSON for traderData.
    Uses no spaces to stay within IMC's ~3,750 char/tick stdout limit.
    """
    return json.dumps(memory, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Order manager
# ---------------------------------------------------------------------------

class OrderManager:
    """
    Tracks position and remaining buy/sell capacity. Enforces position limits
    by capping every order at the remaining capacity before appending it.

    Usage:
        mgr = OrderManager(product, state.position[product], LIMIT)
        mgr.buy(price, qty)   # positive quantity = buy order
        mgr.sell(price, qty)  # qty is treated as positive; submitted as negative
        orders = mgr.flush()  # returns List[Order] and clears internal list

    projected() returns physical position + all pending order quantities.
    This is the correct number to check before submitting, not bare position.

    Mirrors trader_v15.py Manager class (verified lines 187-209).
    """

    def __init__(self, product: str, position: int, limit: int) -> None:
        self.product = product
        self.position = int(position)
        self.limit = int(limit)
        self.buy_cap = max(0, limit - position)
        self.sell_cap = max(0, limit + position)
        self._orders: List[Order] = []

    def projected(self) -> int:
        """Current position plus all pending (unfilled) orders."""
        return self.position + sum(o.quantity for o in self._orders)

    def buy(self, price: int, qty: int) -> None:
        """Submit a buy limit order. Silently capped at remaining buy capacity."""
        size = min(max(0, int(qty)), self.buy_cap)
        if size > 0:
            self._orders.append(Order(self.product, int(price), size))
            self.buy_cap -= size

    def sell(self, price: int, qty: int) -> None:
        """Submit a sell limit order. qty positive; stored as negative quantity."""
        size = min(max(0, int(qty)), self.sell_cap)
        if size > 0:
            self._orders.append(Order(self.product, int(price), -size))
            self.sell_cap -= size

    def flush(self) -> List[Order]:
        orders = self._orders
        self._orders = []
        return orders


# ---------------------------------------------------------------------------
# Options math  (no scipy — Abramowitz-Stegun approximation)
# ---------------------------------------------------------------------------

def norm_pdf(x: float) -> float:
    """
    Standard normal probability density function: N'(x) = exp(-0.5*x^2) / sqrt(2*pi).
    Required for Greeks (delta, gamma, vega). Handles extreme x safely — for
    very large |x|, exp underflows to 0.0 (correct behaviour, no exception).
    """
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def norm_cdf(x: float) -> float:
    """
    Normal CDF via Abramowitz-Stegun polynomial approximation (formula 26.2.17).
    Max absolute error: 7.5e-8.

    NOTE: Frankfurt Hedgehogs (2nd global, P3) used the simpler stdlib alternative:
        from statistics import NormalDist
        _N = NormalDist()
        cdf_value = _N.cdf(x)
    'statistics' is in IMC's permitted import list — prefer that over this function
    unless you want zero external state. This approximation remains here as a
    drop-in for environments where even stdlib imports are restricted.
    """
    t = 1.0 / (1.0 + 0.2316419 * abs(x))
    poly = t * (
        0.319381530
        + t * (
            -0.356563782
            + t * (
                1.781477937
                + t * (-1.821255978 + t * 1.330274429)
            )
        )
    )
    pdf = math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)
    cdf = 1.0 - pdf * poly
    return cdf if x >= 0.0 else 1.0 - cdf


def black_scholes_call(S: float, K: float, T: float, sigma: float, r: float = 0.0) -> float:
    """
    Black-Scholes European call price.
    S: spot price, K: strike, T: time to expiry (in years or fraction of round),
    sigma: implied vol, r: risk-free rate (default 0 — standard for Prosperity).
    Returns intrinsic value max(S-K, 0) when T<=0 or sigma<=0.
    Returns 0.0 if S or K are non-positive (guards against math.log crash).
    """
    if S <= 0.0 or K <= 0.0:
        return 0.0
    if T <= 0.0 or sigma <= 0.0:
        return max(S - K, 0.0)
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)


def black_scholes_put(S: float, K: float, T: float, sigma: float, r: float = 0.0) -> float:
    """
    Black-Scholes European put price via put-call parity.
    put = call - S + K * exp(-rT)
    """
    call = black_scholes_call(S, K, T, sigma, r)
    return call - S + K * math.exp(-r * T)


def black_scholes_delta_call(S: float, K: float, T: float, sigma: float, r: float = 0.0) -> float:
    """
    Delta of a European call option = N(d1). Ranges from 0 (deep OTM) to 1 (deep ITM).

    Interpretation: for a 1-unit increase in the underlying, the call price changes
    by approximately delta. Use to size hedges and compare options across strikes.

    At expiry (T=0): 1.0 if S > K, 0.0 if S <= K.
    Returns 0.0 for non-positive S or K (guards math.log crash).
    """
    if S <= 0.0 or K <= 0.0:
        return 0.0
    if T <= 0.0 or sigma <= 0.0:
        return 1.0 if S > K else 0.0
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    return norm_cdf(d1)


def black_scholes_gamma(S: float, K: float, T: float, sigma: float, r: float = 0.0) -> float:
    """
    Gamma of a European option (identical for call and put) = N'(d1) / (S * sigma * sqrt(T)).

    Interpretation: how quickly delta changes as the underlying moves. Highest
    for ATM options near expiry. Use to understand convexity exposure.

    WARNING: gamma is very large for ATM options with small T and sigma. This is
    mathematically correct — it reflects real convexity risk. Callers should be
    aware that large gamma means delta hedges go stale quickly.

    Returns 0.0 for non-positive S, K, T, or sigma (degenerate inputs).
    """
    if S <= 0.0 or K <= 0.0 or T <= 0.0 or sigma <= 0.0:
        return 0.0
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    return norm_pdf(d1) / (S * sigma * sqrt_T)


def black_scholes_vega(S: float, K: float, T: float, sigma: float, r: float = 0.0) -> float:
    """
    Vega of a European option (identical for call and put) = S * N'(d1) * sqrt(T).

    Interpretation: how much the option price changes for a 1-unit increase in
    sigma (implied volatility). Use to normalize IV deviations to price terms:
        price_edge = iv_deviation * vega

    This lets you compare mispricing across strikes on the same scale.
    Returns 0.0 for non-positive S, K, T, or sigma.
    """
    if S <= 0.0 or K <= 0.0 or T <= 0.0 or sigma <= 0.0:
        return 0.0
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    return S * norm_pdf(d1) * sqrt_T


def implied_vol_call(target_price: float, S: float, K: float, T: float,
                     r: float = 0.0, iterations: int = 60) -> float:
    """
    Implied volatility of a European call via bisection. Returns the sigma such
    that black_scholes_call(S, K, T, sigma, r) ≈ target_price.

    WHY BISECTION: monotone, stable, no derivatives needed, 60 iterations gives
    precision of ~4e-18 — far beyond needed. Newton-Raphson is faster but can
    diverge for deep ITM/OTM options where vega → 0.

    RETURN VALUES:
    - Returns 1e-6 (near-zero vol) if:
        * target_price is at or below discounted intrinsic (no time value to fit)
        * T <= 0 or S/K non-positive
    - Returns 5.0 (500% vol, the search ceiling) if market price exceeds what
      even the highest vol produces. In Prosperity this should never happen
      for reasonably priced instruments.

    CRITICAL USAGE NOTE — time units must match:
        If T is in "ticks remaining / total_ticks", then sigma is in
        "vol per tick-fraction" units. If T is in years, sigma is annualised.
        Use the same time convention consistently throughout one product's logic.
        Mixing units produces correct-looking but completely wrong IVs.

    DEEP ITM/OTM WARNING:
        When extrinsic value is tiny (deep ITM or far OTM), a one-tick price
        change creates a huge IV change. This is not a bug — it reflects real
        instability of IV at extremes. Filter out strikes where:
            market_price - intrinsic < min_extrinsic_threshold
        before calling this function in production.
    """
    if S <= 0.0 or K <= 0.0 or T <= 0.0:
        return 1e-6
    intrinsic = max(S - K * math.exp(-r * T), 0.0)
    if target_price <= intrinsic + 1e-9:
        return 1e-6
    lo, hi = 1e-6, 5.0
    for _ in range(iterations):
        mid_vol = (lo + hi) / 2.0
        if black_scholes_call(S, K, T, mid_vol, r) < target_price:
            lo = mid_vol
        else:
            hi = mid_vol
    return (lo + hi) / 2.0


def vol_smile_iv(strike: float, spot: float, time_remaining: float,
                 a: float, b: float, c: float) -> float:
    """
    Quadratic volatility smile: IV(m) = a*m^2 + b*m + c
    where m = log(strike/spot) / sqrt(time_remaining).

    Fit a, b, c from observed market IVs across visible strikes using least squares.
    Use the returned IV as the sigma argument to black_scholes_call/put.

    WARNING: returns 0.0 for non-positive inputs or when the smile fit produces a
    negative IV (possible for extreme strikes with a poor fit). black_scholes_call
    will then return intrinsic value — correct at expiry but wrong during option
    lifetime. Caller should check for 0.0 return and treat it as "smile fit
    unreliable at this strike" rather than assuming the option has zero time value.
    """
    if time_remaining <= 0.0 or strike <= 0.0 or spot <= 0.0:
        return 0.0
    m = math.log(strike / spot) / math.sqrt(time_remaining)
    iv = a * m * m + b * m + c
    return max(0.0, iv)  # negative IV means smile fit is poor at this strike


# ---------------------------------------------------------------------------
# Olivia detection
# ---------------------------------------------------------------------------

def olivia_update(state: dict, market_trades: dict, product: str,
                  lot_threshold: int = 14) -> Tuple[dict, Optional[str]]:
    """
    Tracks the running daily high/low for a product and detects Olivia's signal.

    Olivia's pattern: buys at new daily lows, sells at new daily highs, in
    approximately 15-lot sizes. Detection without trader IDs: a new daily
    extremum hit with lot_threshold or more lots = Olivia.

    Returns (updated_state, signal) where signal is "BUY", "SELL", or None.

    CALLER RESPONSIBILITY — day reset:
        Olivia's daily_low / daily_high must reset at the start of each new day.
        Detect a new day by checking if state.timestamp has wrapped back to a
        small value (e.g., < previous timestamp by more than 50,000 steps).
        On new day: pass an empty dict as `state` to reset.

    From Round 5 onward, trader IDs are visible. Use direct detection instead:
        for trade in market_trades.get(product, []):
            if trade.buyer == "Olivia": signal = "BUY"
            if trade.seller == "Olivia": signal = "SELL"
    """
    daily_low: Optional[float] = state.get("daily_low")
    daily_high: Optional[float] = state.get("daily_high")
    signal: Optional[str] = None

    for trade in market_trades.get(product, []):
        price = float(trade.price)
        qty = abs(int(trade.quantity))

        if daily_low is None:
            # First trade of the day: initialise, no signal yet
            daily_low = price
            daily_high = price
            continue

        # Use <= / >= (non-strict) to match COMPETITIVE_INTEL pattern and catch
        # Olivia re-testing the same extremum with 14+ lots on subsequent ticks.
        # Strict < / > would miss these repeat signals at the same price level.
        is_new_low = price <= daily_low
        is_new_high = price >= daily_high

        daily_low = min(daily_low, price)
        daily_high = max(daily_high, price)

        if is_new_low and qty >= lot_threshold:
            signal = "BUY"
        elif is_new_high and qty >= lot_threshold:
            signal = "SELL"

    state["daily_low"] = daily_low
    state["daily_high"] = daily_high
    return state, signal


# ---------------------------------------------------------------------------
# Quick self-test  (run: python3 tools/prosperity_utils.py)
# ---------------------------------------------------------------------------

def _self_test() -> None:
    print("Running self-tests...")

    # norm_cdf
    assert abs(norm_cdf(0.0) - 0.5) < 1e-6, "norm_cdf(0) != 0.5"
    assert abs(norm_cdf(1.96) - 0.975) < 1e-3, "norm_cdf(1.96) off"
    assert abs(norm_cdf(-1.96) - 0.025) < 1e-3, "norm_cdf(-1.96) off"
    assert norm_cdf(10.0) > 0.9999, "norm_cdf(10) should be ~1"

    # black_scholes_call — ATM call, T=1, sigma=0.2
    call = black_scholes_call(100, 100, 1.0, 0.20)
    assert 7.0 < call < 9.0, f"ATM BS call out of expected range: {call:.4f}"

    # put-call parity: call - put = S - K*exp(-rT)  (with r=0: = S - K)
    put = black_scholes_put(100, 100, 1.0, 0.20)
    assert abs((call - put) - 0.0) < 1e-8, "Put-call parity violated"

    # black_scholes expiry
    assert black_scholes_call(110, 100, 0.0, 0.20) == 10.0, "Expired ITM call != intrinsic"
    assert black_scholes_call(90, 100, 0.0, 0.20) == 0.0, "Expired OTM call != 0"

    # black_scholes zero/negative price guard (would crash with math.log without guard)
    assert black_scholes_call(0.0, 100, 1.0, 0.20) == 0.0, "S=0 should return 0"
    assert black_scholes_call(100, 0.0, 1.0, 0.20) == 0.0, "K=0 should return 0"
    assert black_scholes_put(0.0, 100, 1.0, 0.20) == 100.0, "Put with S=0 should return K"

    # vol_smile_iv negative IV clamped to 0
    iv = vol_smile_iv(200, 100, 1.0, a=0.1, b=0.0, c=-5.0)  # produces negative raw IV
    assert iv == 0.0, f"Negative smile IV should be clamped to 0, got {iv}"
    iv = vol_smile_iv(100, 100, 1.0, a=0.1, b=0.0, c=0.3)   # normal case
    assert iv > 0.0, "Valid smile IV should be positive"
    assert vol_smile_iv(100, 100, 0.0, 0.1, 0.0, 0.3) == 0.0, "T=0 should return 0"

    # norm_pdf
    assert abs(norm_pdf(0.0) - 1.0 / math.sqrt(2.0 * math.pi)) < 1e-12, "norm_pdf(0) wrong"
    assert norm_pdf(100.0) == 0.0, "norm_pdf for extreme x should underflow to 0.0"
    assert norm_pdf(-1.0) == norm_pdf(1.0), "norm_pdf must be symmetric"

    # black_scholes_delta_call
    delta_atm = black_scholes_delta_call(100, 100, 1.0, 0.20)
    assert 0.45 < delta_atm < 0.65, f"ATM delta should be near 0.5, got {delta_atm}"
    assert black_scholes_delta_call(200, 100, 1.0, 0.20) > 0.90, "Deep ITM delta should be near 1"
    assert black_scholes_delta_call(50, 100, 1.0, 0.20) < 0.10, "Deep OTM delta should be near 0"
    assert black_scholes_delta_call(110, 100, 0.0, 0.20) == 1.0, "Expired ITM delta = 1"
    assert black_scholes_delta_call(90, 100, 0.0, 0.20) == 0.0, "Expired OTM delta = 0"
    assert black_scholes_delta_call(0.0, 100, 1.0, 0.20) == 0.0, "S=0 delta should be 0"

    # black_scholes_gamma
    gamma_atm = black_scholes_gamma(100, 100, 1.0, 0.20)
    assert gamma_atm > 0.0, "Gamma must be positive"
    # Gamma is highest ATM — should exceed gamma of OTM option with same params
    gamma_otm = black_scholes_gamma(100, 150, 1.0, 0.20)
    assert gamma_atm > gamma_otm, "ATM gamma > OTM gamma"
    assert black_scholes_gamma(100, 100, 0.0, 0.20) == 0.0, "T=0 gamma = 0"
    assert black_scholes_gamma(0.0, 100, 1.0, 0.20) == 0.0, "S=0 gamma = 0"

    # black_scholes_vega
    vega_atm = black_scholes_vega(100, 100, 1.0, 0.20)
    assert vega_atm > 0.0, "Vega must be positive"
    # Vega * sigma_change ≈ price change — numerical check
    price_low = black_scholes_call(100, 100, 1.0, 0.20)
    price_high = black_scholes_call(100, 100, 1.0, 0.21)
    vega_approx = (price_high - price_low) / 0.01
    assert abs(vega_atm - vega_approx) < 0.05, f"Vega numerical check failed: {vega_atm} vs {vega_approx}"
    assert black_scholes_vega(100, 100, 0.0, 0.20) == 0.0, "T=0 vega = 0"

    # implied_vol_call — round-trip: IV of a price computed with known sigma should recover sigma
    for test_sigma in [0.10, 0.20, 0.40, 0.80]:
        price = black_scholes_call(100, 100, 1.0, test_sigma)
        recovered = implied_vol_call(price, 100, 100, 1.0)
        assert abs(recovered - test_sigma) < 1e-6, \
            f"IV round-trip failed: input {test_sigma}, recovered {recovered}"

    # implied_vol_call — edge cases
    assert implied_vol_call(0.0, 100, 100, 1.0) == 1e-6, "Zero price → near-zero vol"
    assert implied_vol_call(-1.0, 100, 100, 1.0) == 1e-6, "Negative price → near-zero vol"
    assert implied_vol_call(5.0, 100, 100, 0.0) == 1e-6, "T=0 → near-zero vol"
    assert implied_vol_call(0.0, 0.0, 100, 1.0) == 1e-6, "S=0 → near-zero vol"
    # Below intrinsic returns near-zero vol (not an error)
    intrinsic = 20.0  # S=120, K=100, T=1 → intrinsic = 20
    assert implied_vol_call(intrinsic - 0.01, 120, 100, 1.0) == 1e-6, \
        "Price below intrinsic → near-zero vol"

    # ema
    assert ema(None, 5.0, 0.1) == 5.0, "ema(None) should return current"
    assert abs(ema(10.0, 20.0, 0.5) - 15.0) < 1e-9, "ema(10, 20, 0.5) != 15"
    assert abs(ema(10.0, 20.0, 1.0) - 20.0) < 1e-9, "ema with alpha=1 != current"

    # OrderManager
    mgr = OrderManager("TEST", position=5, limit=10)
    assert mgr.buy_cap == 5
    assert mgr.sell_cap == 15
    mgr.buy(100, 3)
    assert mgr.buy_cap == 2
    assert mgr.projected() == 8
    mgr.sell(95, 20)   # should be capped at sell_cap=15
    orders = mgr.flush()
    assert len(orders) == 2
    assert orders[0].quantity == 3   # buy
    assert orders[1].quantity == -15  # sell capped

    # load/dump memory
    mem = load_memory("")
    assert mem == {}
    mem = load_memory("{bad json")
    assert mem == {}
    mem = load_memory('{"key": 1}')
    assert mem == {"key": 1}
    assert load_memory(dump_memory({"x": 42})) == {"x": 42}

    # book utilities — construct a mock OrderDepth
    od = OrderDepth()
    od.buy_orders = {100: 10, 98: 5, 96: 20}   # volumes positive
    od.sell_orders = {102: -8, 104: -3, 106: -15}  # volumes negative

    assert best_bid(od) == 100
    assert best_ask(od) == 102
    assert abs(raw_mid(od) - 101.0) < 1e-9

    vm = vwap_mid(od, levels=3)
    assert vm is not None and 99.0 < vm < 103.0, f"vwap_mid out of range: {vm}"

    wm = wall_mid(od)
    # Frankfurt-style: min(buy_orders.keys())=96, max(sell_orders.keys())=106
    assert wm is not None and abs(wm - (96 + 106) / 2.0) < 1e-9, f"wall_mid wrong: {wm}"

    tm = thick_mid(od, levels=3)
    # thick_bid = highest-volume bid in top 3 = price 96 (vol 20)
    # thick_ask = highest-volume ask in top 3 = price 106 (vol -15, abs=15)
    assert tm is not None and abs(tm - (96 + 106) / 2.0) < 1e-9, f"thick_mid wrong: {tm}"

    # wall_mid and thick_mid differ when outermost != highest-volume level
    # Buy: thin order at 100 (outermost=90), thick order at 95
    # Ask: thin order at 105, thick order at 120 (outermost=120)
    od2 = OrderDepth()
    od2.buy_orders = {95: 20, 90: 1}    # highest vol at 95, outermost (lowest) at 90
    od2.sell_orders = {105: -1, 120: -20}  # highest vol at 120, outermost (highest) at 120
    wm2 = wall_mid(od2)
    tm2 = thick_mid(od2, levels=2)
    # wall_mid: (min_bid=90 + max_ask=120) / 2 = 105
    assert abs(wm2 - (90 + 120) / 2.0) < 1e-9, f"wall_mid should use outermost: {wm2}"
    # thick_mid: (highest-vol bid=95 + highest-vol ask=120) / 2 = 107.5
    assert abs(tm2 - (95 + 120) / 2.0) < 1e-9, f"thick_mid should use highest vol: {tm2}"
    assert abs(wm2 - tm2) > 1.0, "wall_mid and thick_mid should differ in this case"

    mp = micro_price(od)
    # micro = (102*10 + 100*8) / (10+8) = (1020+800)/18 = 1820/18 ≈ 101.11
    assert mp is not None and abs(mp - (102 * 10 + 100 * 8) / 18.0) < 1e-6, f"micro_price wrong: {mp}"

    imb = book_imbalance(od, levels=1)
    # (10 - 8) / (10 + 8) = 2/18 ≈ 0.111
    assert abs(imb - 2 / 18.0) < 1e-9, f"book_imbalance wrong: {imb}"

    # Olivia detection
    class FakeTrade:
        def __init__(self, price, quantity):
            self.price = price
            self.quantity = quantity

    olivia_state: dict = {}
    trades = {"PROD": [FakeTrade(200, 5)]}  # first trade: init only, no signal
    olivia_state, sig = olivia_update(olivia_state, trades, "PROD")
    assert sig is None, "First trade should not signal"
    assert olivia_state["daily_low"] == 200

    trades = {"PROD": [FakeTrade(190, 15)]}  # new low with 15 lots → BUY
    olivia_state, sig = olivia_update(olivia_state, trades, "PROD")
    assert sig == "BUY", f"Expected BUY, got {sig}"

    trades = {"PROD": [FakeTrade(210, 15)]}  # new high with 15 lots → SELL
    olivia_state, sig = olivia_update(olivia_state, trades, "PROD")
    assert sig == "SELL", f"Expected SELL, got {sig}"

    trades = {"PROD": [FakeTrade(185, 5)]}  # new low but only 5 lots → no signal
    olivia_state, sig = olivia_update(olivia_state, trades, "PROD")
    assert sig is None, f"Small lot new low should not signal, got {sig}"

    # re-test of same low with 14+ lots should still signal (non-strict <=)
    trades = {"PROD": [FakeTrade(185, 15)]}  # same price as current low, 15 lots → BUY
    olivia_state, sig = olivia_update(olivia_state, trades, "PROD")
    assert sig == "BUY", f"Re-test of same low with 15 lots should signal BUY, got {sig}"

    print("All tests passed.")


if __name__ == "__main__":
    _self_test()
