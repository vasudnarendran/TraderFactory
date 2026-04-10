#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


OUTPUT_DIR = Path(__file__).resolve().parents[2] / "generated" / "reports" / "official_trade_quality"
MARKOUT_HORIZONS = (1, 2, 4, 8)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a fill-level trade quality and comparison report from official Prosperity submission logs.",
    )
    parser.add_argument("log_path", type=Path, help="Path to the primary official .log JSON file.")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Optional baseline official .log JSON file for direct comparison.",
    )
    parser.add_argument(
        "--primary-json",
        type=Path,
        default=None,
        help="Optional primary official .json file. Defaults to sibling of log_path.",
    )
    parser.add_argument(
        "--baseline-json",
        type=Path,
        default=None,
        help="Optional baseline official .json file. Defaults to sibling of --baseline.",
    )
    parser.add_argument(
        "--output-prefix",
        default="",
        help="Optional prefix for generated files in the output directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output directory. Defaults to generated/reports/official_trade_quality.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict JSON in {path}")
    return data


def infer_json_path(log_path: Path) -> Path:
    sibling = log_path.with_suffix(".json")
    if sibling.exists():
        return sibling
    raise FileNotFoundError(f"Could not infer sibling json for {log_path}")


def parse_activities_log(raw: str) -> tuple[dict[tuple[int, str], dict[str, Any]], dict[str, list[int]], dict[str, float]]:
    snapshots: dict[tuple[int, str], dict[str, Any]] = {}
    product_timestamps: dict[str, list[int]] = defaultdict(list)
    latest_pnl: dict[str, float] = {}

    reader = csv.DictReader(io.StringIO(raw), delimiter=";")
    for row in reader:
        timestamp = int(row["timestamp"])
        product = str(row["product"])
        best_bid = float(row["bid_price_1"]) if row.get("bid_price_1") else None
        best_ask = float(row["ask_price_1"]) if row.get("ask_price_1") else None
        mid_price = float(row["mid_price"])
        pnl = float(row["profit_and_loss"])
        snapshots[(timestamp, product)] = {
            "timestamp": timestamp,
            "product": product,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid_price": mid_price,
            "spread": (best_ask - best_bid) if best_bid is not None and best_ask is not None else None,
            "profit_and_loss": pnl,
        }
        product_timestamps[product].append(timestamp)
        latest_pnl[product] = pnl

    for product in product_timestamps:
        product_timestamps[product] = sorted(set(product_timestamps[product]))

    return snapshots, product_timestamps, latest_pnl


def parse_positions(raw_positions: list[dict[str, Any]]) -> dict[str, int]:
    positions: dict[str, int] = {}
    for row in raw_positions:
        symbol = str(row.get("symbol", ""))
        if not symbol:
            continue
        try:
            positions[symbol] = int(float(row.get("quantity", 0)))
        except (TypeError, ValueError):
            continue
    return positions


def normalize_submission_trades(trade_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fills: list[dict[str, Any]] = []
    for trade in trade_history:
        buyer = str(trade.get("buyer", "") or "")
        seller = str(trade.get("seller", "") or "")
        if buyer != "SUBMISSION" and seller != "SUBMISSION":
            continue
        side = "BUY" if buyer == "SUBMISSION" else "SELL"
        fills.append(
            {
                "timestamp": int(trade["timestamp"]),
                "product": str(trade["symbol"]),
                "side": side,
                "price": int(float(trade["price"])),
                "quantity": int(float(trade["quantity"])),
            }
        )
    fills.sort(key=lambda row: (row["timestamp"], row["product"], row["side"], row["price"], row["quantity"]))
    return fills


def future_markout(
    fill: dict[str, Any],
    snapshots: dict[tuple[int, str], dict[str, Any]],
    product_timestamps: dict[str, list[int]],
    steps: int,
) -> float | None:
    product = str(fill["product"])
    timestamp = int(fill["timestamp"])
    timestamps = product_timestamps.get(product, [])
    if not timestamps or (timestamp, product) not in snapshots:
        return None
    try:
        index = timestamps.index(timestamp)
    except ValueError:
        return None
    future_index = index + steps
    if future_index >= len(timestamps):
        return None
    future_mid = float(snapshots[(timestamps[future_index], product)]["mid_price"])
    side_sign = 1.0 if fill["side"] == "BUY" else -1.0
    return round((future_mid - float(fill["price"])) * side_sign, 6)


def classify_fill_style(fill: dict[str, Any], snapshot: dict[str, Any]) -> tuple[str, bool, float | None, float | None]:
    best_bid = snapshot.get("best_bid")
    best_ask = snapshot.get("best_ask")
    mid = snapshot.get("mid_price")
    price = float(fill["price"])
    side = str(fill["side"])
    side_sign = 1.0 if side == "BUY" else -1.0
    visible_edge = None if mid is None else round((float(mid) - price) * side_sign, 6)
    edge_vs_touch = None
    worst_side = False
    style = "unknown"

    if side == "BUY" and best_ask is not None:
        edge_vs_touch = round(float(best_ask) - price, 6)
        worst_side = price >= float(best_ask)
        style = "aggressive" if price >= float(best_ask) else "passive"
    elif side == "SELL" and best_bid is not None:
        edge_vs_touch = round(price - float(best_bid), 6)
        worst_side = price <= float(best_bid)
        style = "aggressive" if price <= float(best_bid) else "passive"

    return style, worst_side, visible_edge, edge_vs_touch


def enrich_fills(
    fills: list[dict[str, Any]],
    snapshots: dict[tuple[int, str], dict[str, Any]],
    product_timestamps: dict[str, list[int]],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for fill in fills:
        snapshot = snapshots.get((fill["timestamp"], fill["product"]), {})
        style, worst_side, visible_edge, edge_vs_touch = classify_fill_style(fill, snapshot)
        row = dict(fill)
        row["best_bid"] = snapshot.get("best_bid")
        row["best_ask"] = snapshot.get("best_ask")
        row["mid_price"] = snapshot.get("mid_price")
        row["spread"] = snapshot.get("spread")
        row["profit_and_loss"] = snapshot.get("profit_and_loss")
        row["style"] = style
        row["worst_side"] = worst_side
        row["visible_edge"] = visible_edge
        row["edge_vs_touch"] = edge_vs_touch
        for horizon in MARKOUT_HORIZONS:
            row[f"markout_{horizon}"] = future_markout(fill, snapshots, product_timestamps, horizon)
        enriched.append(row)
    return enriched


def weighted_average(rows: list[dict[str, Any]], field: str) -> float | None:
    total_qty = 0
    total_value = 0.0
    for row in rows:
        value = row.get(field)
        if value is None:
            continue
        qty = int(row["quantity"])
        total_qty += qty
        total_value += float(value) * qty
    if total_qty <= 0:
        return None
    return total_value / total_qty


def sum_weighted_positive(rows: list[dict[str, Any]], field: str) -> tuple[int, int, float]:
    count = 0
    qty = 0
    total = 0.0
    for row in rows:
        value = row.get(field)
        if value is None or float(value) <= 0.0:
            continue
        count += 1
        qty += int(row["quantity"])
        total += float(value) * int(row["quantity"])
    return count, qty, total


def sum_weighted_negative(rows: list[dict[str, Any]], field: str) -> tuple[int, int, float]:
    count = 0
    qty = 0
    total = 0.0
    for row in rows:
        value = row.get(field)
        if value is None or float(value) >= 0.0:
            continue
        count += 1
        qty += int(row["quantity"])
        total += float(value) * int(row["quantity"])
    return count, qty, total


def summarise_fill_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_qty = sum(int(row["quantity"]) for row in rows)
    summary: dict[str, Any] = {
        "fill_count": len(rows),
        "qty": total_qty,
        "avg_price": weighted_average(rows, "price"),
        "avg_visible_edge": weighted_average(rows, "visible_edge"),
        "avg_edge_vs_touch": weighted_average(rows, "edge_vs_touch"),
        "avg_markout_1": weighted_average(rows, "markout_1"),
        "avg_markout_4": weighted_average(rows, "markout_4"),
        "avg_markout_8": weighted_average(rows, "markout_8"),
        "worst_side_fill_count": sum(1 for row in rows if row.get("worst_side")),
        "worst_side_qty": sum(int(row["quantity"]) for row in rows if row.get("worst_side")),
    }
    pos_count, pos_qty, pos_total = sum_weighted_positive(rows, "visible_edge")
    neg_count, neg_qty, neg_total = sum_weighted_negative(rows, "visible_edge")
    summary.update(
        {
            "positive_edge_fill_count": pos_count,
            "positive_edge_qty": pos_qty,
            "positive_edge_sum": pos_total,
            "negative_edge_fill_count": neg_count,
            "negative_edge_qty": neg_qty,
            "negative_edge_sum": neg_total,
        }
    )
    return summary


def summarise_fills(enriched_fills: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "overall": summarise_fill_group(enriched_fills),
        "by_product": {},
        "by_product_side": {},
        "by_product_style": {},
    }

    grouped_product: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_product_side: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    grouped_product_style: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for row in enriched_fills:
        product = str(row["product"])
        grouped_product[product].append(row)
        grouped_product_side[(product, str(row["side"]))].append(row)
        grouped_product_style[(product, str(row["style"]))].append(row)

    summary["by_product"] = {
        product: summarise_fill_group(rows)
        for product, rows in sorted(grouped_product.items())
    }
    summary["by_product_side"] = {
        f"{product}:{side}": summarise_fill_group(rows)
        for (product, side), rows in sorted(grouped_product_side.items())
    }
    summary["by_product_style"] = {
        f"{product}:{style}": summarise_fill_group(rows)
        for (product, style), rows in sorted(grouped_product_style.items())
    }
    return summary


def best_and_worst_fills(enriched_fills: list[dict[str, Any]], field: str, limit: int = 10) -> dict[str, list[dict[str, Any]]]:
    valid = [row for row in enriched_fills if row.get(field) is not None]
    return {
        "best": sorted(valid, key=lambda row: float(row[field]), reverse=True)[:limit],
        "worst": sorted(valid, key=lambda row: float(row[field]))[:limit],
    }


def key_fill(row: dict[str, Any]) -> tuple[Any, ...]:
    return (row["timestamp"], row["product"], row["side"], row["price"], row["quantity"])


def compare_fills(primary: list[dict[str, Any]], baseline: list[dict[str, Any]]) -> dict[str, Any]:
    primary_keys = Counter(key_fill(row) for row in primary)
    baseline_keys = Counter(key_fill(row) for row in baseline)
    added: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []

    primary_lookup = defaultdict(list)
    baseline_lookup = defaultdict(list)
    for row in primary:
        primary_lookup[key_fill(row)].append(row)
    for row in baseline:
        baseline_lookup[key_fill(row)].append(row)

    for key, count in (primary_keys - baseline_keys).items():
        added.extend(primary_lookup[key][:count])
    for key, count in (baseline_keys - primary_keys).items():
        removed.extend(baseline_lookup[key][:count])

    first_divergence = None
    for index, (a, b) in enumerate(zip(primary, baseline)):
        if key_fill(a) != key_fill(b):
            first_divergence = {"index": index, "primary": a, "baseline": b}
            break
    if first_divergence is None and len(primary) != len(baseline):
        first_divergence = {
            "index": min(len(primary), len(baseline)),
            "primary": primary[min(len(primary), len(baseline))] if len(primary) > len(baseline) else None,
            "baseline": baseline[min(len(primary), len(baseline))] if len(baseline) > len(primary) else None,
        }

    return {
        "fill_count_delta": len(primary) - len(baseline),
        "added_fill_count": len(added),
        "removed_fill_count": len(removed),
        "first_divergence": first_divergence,
        "added_fills": added,
        "removed_fills": removed,
    }


def build_log_report(log_payload: dict[str, Any], json_payload: dict[str, Any]) -> dict[str, Any]:
    snapshots, product_timestamps, final_pnl_by_product = parse_activities_log(json_payload.get("activitiesLog", ""))
    fills = normalize_submission_trades(log_payload.get("tradeHistory", []))
    enriched_fills = enrich_fills(fills, snapshots, product_timestamps)
    positions = parse_positions(json_payload.get("positions", []))
    return {
        "profit": float(json_payload.get("profit", 0.0)),
        "positions": positions,
        "final_pnl_by_product": final_pnl_by_product,
        "trade_history_count": len(log_payload.get("tradeHistory", [])),
        "submission_fill_count": len(fills),
        "has_logs": bool(log_payload.get("logs")),
        "fill_summary": summarise_fills(enriched_fills),
        "visible_edge_extremes": best_and_worst_fills(enriched_fills, "visible_edge"),
        "markout4_extremes": best_and_worst_fills(enriched_fills, "markout_4"),
        "fills": enriched_fills,
        "exact_hash_inputs": {
            "activitiesLog": log_payload.get("activitiesLog", ""),
            "tradeHistory": log_payload.get("tradeHistory", []),
            "logs": log_payload.get("logs", []),
        },
    }


def render_fill(row: dict[str, Any]) -> str:
    return (
        f"{row['timestamp']} {row['product']} {row['side']} {row['price']} x{row['quantity']} "
        f"style={row.get('style')} edge={row.get('visible_edge')} m4={row.get('markout_4')}"
    )


def safe_fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, (int, float)):
        return f"{float(value):.{digits}f}"
    return str(value)


def markdown_for_report(
    primary_name: str,
    primary_report: dict[str, Any],
    baseline_name: str | None,
    baseline_report: dict[str, Any] | None,
    comparison: dict[str, Any] | None,
) -> str:
    lines = [
        "Official Trade Quality Report",
        "============================",
        "",
        f"Primary: {primary_name}",
        f"Profit: {primary_report['profit']}",
        f"Final PnL by product: {primary_report['final_pnl_by_product']}",
        f"Final positions: {primary_report['positions']}",
        f"Submission fills: {primary_report['submission_fill_count']}",
        "",
        "Primary fill summary by product:",
    ]
    for product, summary in primary_report["fill_summary"]["by_product"].items():
        lines.append(
            f"- {product}: fills={summary['fill_count']} qty={summary['qty']} "
            f"avg_edge={safe_fmt(summary['avg_visible_edge'])} avg_m4={safe_fmt(summary['avg_markout_4'])} "
            f"worst_side_qty={summary['worst_side_qty']}"
        )

    lines.extend(["", "Worst primary fills by visible edge:"])
    for row in primary_report["visible_edge_extremes"]["worst"][:8]:
        lines.append(f"- {render_fill(row)}")

    lines.extend(["", "Worst primary fills by markout_4:"])
    for row in primary_report["markout4_extremes"]["worst"][:8]:
        lines.append(f"- {render_fill(row)}")

    if baseline_name and baseline_report and comparison:
        lines.extend(
            [
                "",
                f"Baseline: {baseline_name}",
                f"Baseline profit: {baseline_report['profit']}",
                "",
                "Comparison",
                "----------",
                f"Profit delta: {safe_fmt(primary_report['profit'] - baseline_report['profit'])}",
                f"Activities identical: {comparison['activities_identical']}",
                f"Trade history identical: {comparison['trade_history_identical']}",
                f"Logs identical: {comparison['logs_identical']}",
                f"Dormant candidate: {comparison['dormant_candidate']}",
                f"Fill count delta: {comparison['fill_differences']['fill_count_delta']}",
                f"Added fills: {comparison['fill_differences']['added_fill_count']}",
                f"Removed fills: {comparison['fill_differences']['removed_fill_count']}",
                "",
                f"Per-product pnl delta: {comparison['per_product_pnl_delta']}",
                "",
            ]
        )
        first_divergence = comparison["fill_differences"]["first_divergence"]
        if first_divergence:
            lines.append("First divergence:")
            if first_divergence.get("baseline") is not None:
                lines.append(f"- baseline: {render_fill(first_divergence['baseline'])}")
            if first_divergence.get("primary") is not None:
                lines.append(f"- primary: {render_fill(first_divergence['primary'])}")
        if comparison["fill_differences"]["added_fills"]:
            lines.extend(["", "Added fills (first 10):"])
            for row in comparison["fill_differences"]["added_fills"][:10]:
                lines.append(f"- {render_fill(row)}")
        if comparison["fill_differences"]["removed_fills"]:
            lines.extend(["", "Removed fills (first 10):"])
            for row in comparison["fill_differences"]["removed_fills"][:10]:
                lines.append(f"- {render_fill(row)}")

    return "\n".join(lines) + "\n"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()

    log_path = args.log_path.expanduser().resolve()
    primary_json = (args.primary_json.expanduser().resolve() if args.primary_json else infer_json_path(log_path))
    baseline_log = args.baseline.expanduser().resolve() if args.baseline else None
    baseline_json = None
    if baseline_log is not None:
        baseline_json = args.baseline_json.expanduser().resolve() if args.baseline_json else infer_json_path(baseline_log)

    primary_log_payload = load_json(log_path)
    primary_json_payload = load_json(primary_json)
    primary_report = build_log_report(primary_log_payload, primary_json_payload)

    baseline_report = None
    comparison = None
    prefix = args.output_prefix
    if not prefix:
        prefix = log_path.stem
        if baseline_log is not None:
            prefix = f"{baseline_log.stem}_vs_{log_path.stem}"

    if baseline_log is not None and baseline_json is not None:
        baseline_log_payload = load_json(baseline_log)
        baseline_json_payload = load_json(baseline_json)
        baseline_report = build_log_report(baseline_log_payload, baseline_json_payload)
        comparison = {
            "activities_identical": baseline_log_payload.get("activitiesLog") == primary_log_payload.get("activitiesLog"),
            "trade_history_identical": baseline_log_payload.get("tradeHistory") == primary_log_payload.get("tradeHistory"),
            "logs_identical": baseline_log_payload.get("logs") == primary_log_payload.get("logs"),
            "dormant_candidate": (
                baseline_log_payload.get("activitiesLog") == primary_log_payload.get("activitiesLog")
                and baseline_log_payload.get("tradeHistory") == primary_log_payload.get("tradeHistory")
                and baseline_log_payload.get("logs") == primary_log_payload.get("logs")
            ),
            "per_product_pnl_delta": {
                product: float(primary_report["final_pnl_by_product"].get(product, 0.0))
                - float(baseline_report["final_pnl_by_product"].get(product, 0.0))
                for product in sorted(
                    set(primary_report["final_pnl_by_product"]) | set(baseline_report["final_pnl_by_product"])
                )
            },
            "fill_differences": compare_fills(primary_report["fills"], baseline_report["fills"]),
        }

    output_dir = args.output_dir.expanduser().resolve() if args.output_dir else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    json_out = output_dir / f"{prefix}_official_trade_quality_report.json"
    md_out = output_dir / f"{prefix}_official_trade_quality_report.md"
    primary_csv = output_dir / f"{prefix}_primary_fills.csv"
    payload = {
        "primary_log": str(log_path),
        "primary_json": str(primary_json),
        "primary_report": primary_report,
        "baseline_log": str(baseline_log) if baseline_log else None,
        "baseline_json": str(baseline_json) if baseline_json else None,
        "baseline_report": baseline_report,
        "comparison": comparison,
    }
    json_out.write_text(json.dumps(payload, indent=2) + "\n")
    md_out.write_text(
        markdown_for_report(
            log_path.stem,
            primary_report,
            baseline_log.stem if baseline_log else None,
            baseline_report,
            comparison,
        )
    )
    write_csv(primary_csv, primary_report["fills"])

    if baseline_report is not None and comparison is not None:
        write_csv(output_dir / f"{prefix}_baseline_fills.csv", baseline_report["fills"])
        write_csv(output_dir / f"{prefix}_added_fills.csv", comparison["fill_differences"]["added_fills"])
        write_csv(output_dir / f"{prefix}_removed_fills.csv", comparison["fill_differences"]["removed_fills"])

    print(f"Wrote {json_out}")
    print(f"Wrote {md_out}")
    print(f"Wrote {primary_csv}")
    if baseline_report is not None and comparison is not None:
        print(f"Dormant candidate: {comparison['dormant_candidate']}")
        print(f"Profit delta vs baseline: {primary_report['profit'] - baseline_report['profit']:.6f}")
        print(f"Per-product pnl delta: {comparison['per_product_pnl_delta']}")


if __name__ == "__main__":
    main()
