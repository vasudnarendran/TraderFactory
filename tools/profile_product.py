"""
Quick data profiler for any Prosperity product CSV.

Usage:
    python tools/profile_product.py data/prices_round_3_day_-1.csv
    python tools/profile_product.py data/prices_round_3_day_-1.csv --product SOME_PRODUCT
"""
import sys
import math
import argparse
from collections import defaultdict


def parse_csv(path):
    rows = []
    with open(path) as f:
        header = f.readline().strip().split(";")
        for line in f:
            parts = line.strip().split(";")
            if len(parts) < len(header):
                continue
            rows.append(dict(zip(header, parts)))
    return rows


def safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def autocorr(series, lag=1):
    n = len(series)
    if n <= lag:
        return float("nan")
    mean = sum(series) / n
    diffs = [x - mean for x in series]
    num = sum(diffs[i] * diffs[i + lag] for i in range(n - lag))
    denom = sum(d * d for d in diffs)
    return num / denom if denom > 0 else float("nan")


def linear_fit(xs, ys):
    n = len(xs)
    if n < 2:
        return 0.0, ys[0] if ys else 0.0
    sx = sum(xs)
    sy = sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    if denom == 0:
        return 0.0, sy / n
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return slope, intercept


def profile_product(rows, product):
    data = [r for r in rows if r.get("product") == product]
    if not data:
        print(f"  No rows found for {product}")
        return

    timestamps = [int(r["timestamp"]) for r in data]
    mids = [safe_float(r.get("mid_price")) for r in data]
    mids = [m for m in mids if m is not None and m > 0]

    spreads = []
    for r in data:
        b1 = safe_float(r.get("bid_price_1"))
        a1 = safe_float(r.get("ask_price_1"))
        if b1 and a1 and b1 > 0 and a1 > 0:
            spreads.append(a1 - b1)

    bid_vols = [safe_float(r.get("bid_volume_1")) for r in data]
    ask_vols = [safe_float(r.get("ask_volume_1")) for r in data]
    bid_vols = [v for v in bid_vols if v is not None and v > 0]
    ask_vols = [v for v in ask_vols if v is not None and v > 0]

    returns = [mids[i + 1] - mids[i] for i in range(len(mids) - 1)]
    abs_returns = [abs(r) for r in returns]

    # Drift via linear fit on mid
    valid_ts = [int(data[i]["timestamp"]) for i in range(len(data)) if safe_float(data[i].get("mid_price")) is not None and safe_float(data[i].get("mid_price")) > 0]
    valid_mids = [safe_float(data[i].get("mid_price")) for i in range(len(data)) if safe_float(data[i].get("mid_price")) is not None and safe_float(data[i].get("mid_price")) > 0]
    slope, intercept = linear_fit(valid_ts, valid_mids)

    # Residuals from linear trend
    residuals = [valid_mids[i] - (intercept + slope * valid_ts[i]) for i in range(len(valid_mids))]
    residual_std = math.sqrt(sum(r * r for r in residuals) / len(residuals)) if residuals else 0.0

    # Autocorrelation of returns (lag 1)
    ac1 = autocorr(returns, lag=1)
    ac2 = autocorr(returns, lag=2)

    # PnL if available
    pnls = [safe_float(r.get("profit_and_loss")) for r in data]
    pnls = [p for p in pnls if p is not None]

    print(f"\n{'='*60}")
    print(f"  {product}  ({len(data)} rows, {len(set(r['day'] for r in data))} day(s))")
    print(f"{'='*60}")

    print(f"\n  PRICE")
    if mids:
        print(f"    range:       {min(mids):.1f} – {max(mids):.1f}")
        print(f"    mean:        {sum(mids)/len(mids):.2f}")
        print(f"    start/end:   {mids[0]:.1f} → {mids[-1]:.1f}  (Δ {mids[-1]-mids[0]:+.1f})")

    print(f"\n  DRIFT")
    print(f"    slope:       {slope:.6f} per timestamp")
    print(f"    over day:    {slope * (max(timestamps) - min(timestamps)):+.2f} total")
    print(f"    residual σ:  {residual_std:.3f}  (noise around trend)")

    print(f"\n  SPREAD")
    if spreads:
        print(f"    mean:        {sum(spreads)/len(spreads):.2f}")
        print(f"    median:      {sorted(spreads)[len(spreads)//2]:.1f}")
        print(f"    min/max:     {min(spreads):.0f} / {max(spreads):.0f}")
        tight = sum(1 for s in spreads if s <= sum(spreads)/len(spreads) * 0.75)
        print(f"    tight (<75% avg): {tight}/{len(spreads)} ({100*tight/len(spreads):.0f}%)")

    print(f"\n  VOLUME (best bid/ask level 1)")
    if bid_vols:
        print(f"    avg bid vol: {sum(bid_vols)/len(bid_vols):.1f}")
    if ask_vols:
        print(f"    avg ask vol: {sum(ask_vols)/len(ask_vols):.1f}")

    print(f"\n  RETURNS (step-to-step mid change)")
    if returns:
        print(f"    mean |move|: {sum(abs_returns)/len(abs_returns):.3f} per step")
        print(f"    max  |move|: {max(abs_returns):.2f}")
        nonzero = sum(1 for r in returns if abs(r) > 0)
        print(f"    active steps:{nonzero}/{len(returns)} ({100*nonzero/len(returns):.0f}%)")
        up = sum(1 for r in returns if r > 0)
        dn = sum(1 for r in returns if r < 0)
        print(f"    up/dn steps: {up}/{dn}")

    print(f"\n  AUTOCORRELATION (mid returns)")
    print(f"    lag-1:       {ac1:+.3f}  {'← mean-reverting' if ac1 < -0.1 else '← trending' if ac1 > 0.1 else '← neutral'}")
    print(f"    lag-2:       {ac2:+.3f}")

    if len(mids) >= 4:
        chunk = len(mids) // 4
        q_starts = [mids[i * chunk] for i in range(4)]
        q_ends = [mids[min((i + 1) * chunk, len(mids)) - 1] for i in range(4)]
        q_gains = [q_ends[i] - q_starts[i] for i in range(4)]
        print(f"\n  PRICE QUARTILES (directional drift per quarter)")
        for i, g in enumerate(q_gains):
            print(f"    Q{i+1}: {g:+.2f}")

    if pnls and pnls[-1] != 0:
        print(f"\n  PnL (from log, final): {pnls[-1]:.2f}")

    # Archetype hint
    # Use drift SNR: total drift vs expected random-walk noise (mean_move * sqrt(n))
    # Bid-ask bounce causes lag-1 autocorr ≈ -0.5 regardless of drift, so don't use AC alone
    print(f"\n  ARCHETYPE HINT")
    drift_magnitude = abs(mids[-1] - mids[0]) if mids else 0.0
    rw_noise = (sum(abs_returns) / len(abs_returns) * math.sqrt(len(returns))) if returns else 1.0
    drift_snr = drift_magnitude / rw_noise if rw_noise > 0 else 0.0
    net_drift_per_step = slope * (max(timestamps) - min(timestamps)) / len(valid_mids) if valid_mids else 0.0
    if drift_snr > 3.0:
        direction = "upward" if mids[-1] > mids[0] else "downward"
        print(f"    → STRONG DRIFT  (SNR={drift_snr:.1f}x, {direction}, +{mids[-1]-mids[0]:+.1f} total)")
        print(f"      Carry/schedule strategy likely appropriate")
    elif not spreads:
        print(f"    → UNCLEAR  (no spread data visible — product may be near-worthless or deep OTM option)")
        print(f"      Examine option chain relationship to underlying")
    elif residual_std < sum(spreads) / len(spreads) * 3:
        avg_spread = sum(spreads) / len(spreads)
        print(f"    → MEAN-REVERTING  (tight residuals, spread={avg_spread:.1f})")
        print(f"      Market-making with fair-value anchor likely appropriate")
    else:
        print(f"    → UNCLEAR  (drift_snr={drift_snr:.1f}, residual_σ={residual_std:.1f})")
        print(f"      Examine further — check for basket/derivative relationships")


def main():
    parser = argparse.ArgumentParser(description="Profile a Prosperity product CSV")
    parser.add_argument("csv", help="Path to prices CSV file")
    parser.add_argument("--product", help="Filter to one product (default: all)")
    args = parser.parse_args()

    rows = parse_csv(args.csv)
    products = sorted(set(r.get("product", "") for r in rows if r.get("product")))

    if args.product:
        if args.product not in products:
            print(f"Product {args.product!r} not found. Available: {products}")
            sys.exit(1)
        products = [args.product]

    print(f"File: {args.csv}")
    print(f"Products: {products}")
    print(f"Total rows: {len(rows)}")

    for product in products:
        profile_product(rows, product)


if __name__ == "__main__":
    main()
