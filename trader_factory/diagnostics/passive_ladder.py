#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


MARKOUT_HORIZONS = (1, 2, 4, 8)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize passive ladder probe events from an official submission log.")
    parser.add_argument("log_path", type=Path, help="Path to the official .log JSON file")
    parser.add_argument(
        "--json-path",
        type=Path,
        default=None,
        help="Optional path to the sibling official .json file. Defaults to log sibling.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional output directory. Defaults to generated/reports/passive_ladder/<log_stem>/",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict JSON in {path}")
    return data


def infer_json_path(log_path: Path) -> Path:
    candidate = log_path.with_suffix(".json")
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"Could not infer sibling json path for {log_path}")


def parse_activities_log(raw: str) -> tuple[dict[tuple[int, str], dict[str, Any]], dict[str, list[int]]]:
    snapshots: dict[tuple[int, str], dict[str, Any]] = {}
    product_timestamps: dict[str, list[int]] = defaultdict(list)
    reader = csv.DictReader(io.StringIO(raw), delimiter=";")
    for row in reader:
        timestamp = int(row["timestamp"])
        product = str(row["product"])
        best_bid = float(row["bid_price_1"]) if row.get("bid_price_1") else None
        best_ask = float(row["ask_price_1"]) if row.get("ask_price_1") else None
        snapshots[(timestamp, product)] = {
            "timestamp": timestamp,
            "product": product,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid_price": float(row["mid_price"]),
            "profit_and_loss": float(row["profit_and_loss"]),
        }
        product_timestamps[product].append(timestamp)
    for product in product_timestamps:
        product_timestamps[product] = sorted(set(product_timestamps[product]))
    return snapshots, product_timestamps


def extract_ladder_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for row in payload.get("logs", []):
        timestamp = int(row.get("timestamp", 0))
        for field in ("lambdaLog", "sandboxLog"):
            text = row.get(field, "") or ""
            for line in text.splitlines():
                line = line.strip()
                if not line.startswith("DIAG "):
                    continue
                try:
                    diag_payload = json.loads(line[5:])
                except json.JSONDecodeError:
                    continue
                for event in diag_payload.get("events", []):
                    event_type = str(event.get("et", ""))
                    if not event_type.startswith("lp_"):
                        continue
                    item = dict(event)
                    item["_log_timestamp"] = timestamp
                    item["_log_field"] = field
                    events.append(item)
    events.sort(key=lambda row: (int(row.get("fill_ts", row.get("ts", 0))), str(row.get("et", ""))))
    return events


def markout_for_horizon(
    timestamp: int,
    product: str,
    price: float,
    side: str,
    snapshots: dict[tuple[int, str], dict[str, Any]],
    product_timestamps: dict[str, list[int]],
    horizon_steps: int,
) -> float | None:
    timestamps = product_timestamps.get(product, [])
    if not timestamps or (timestamp, product) not in snapshots:
        return None
    try:
        index = timestamps.index(timestamp)
    except ValueError:
        return None
    future_index = index + horizon_steps
    if future_index >= len(timestamps):
        return None
    future_mid = float(snapshots[(timestamps[future_index], product)]["mid_price"])
    side_sign = 1.0 if side == "BUY" else -1.0
    return round((future_mid - price) * side_sign, 6)


def safe_avg(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    log_path = args.log_path.expanduser().resolve()
    json_path = args.json_path.expanduser().resolve() if args.json_path else infer_json_path(log_path)
    payload = load_json(log_path)
    json_payload = load_json(json_path)

    output_dir = (
        Path(args.output).expanduser().resolve()
        if args.output
        else (Path(__file__).resolve().parents[2] / "generated" / "reports" / "passive_ladder" / log_path.stem)
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshots, product_timestamps = parse_activities_log(json_payload.get("activitiesLog", ""))
    events = extract_ladder_events(payload)
    fill_events = [row for row in events if row.get("et") == "lp_fill"]
    summary_events = [row for row in events if row.get("et") == "lp_summary"]

    enriched_fills: list[dict[str, Any]] = []
    for row in fill_events:
        fill_ts = int(row["fill_ts"])
        price = float(row["price"])
        side = str(row["side"])
        product = str(row.get("p", "UNKNOWN_PRODUCT"))
        snapshot = snapshots.get((fill_ts, product), {})
        enriched = dict(row)
        enriched["best_bid_fill"] = snapshot.get("best_bid")
        enriched["best_ask_fill"] = snapshot.get("best_ask")
        enriched["mid_fill"] = snapshot.get("mid_price")
        if snapshot.get("mid_price") is not None:
            side_sign = 1.0 if side == "BUY" else -1.0
            enriched["visible_edge_fill"] = round((float(snapshot["mid_price"]) - price) * side_sign, 6)
        else:
            enriched["visible_edge_fill"] = None
        for horizon in MARKOUT_HORIZONS:
            enriched[f"markout_{horizon}"] = markout_for_horizon(
                fill_ts,
                product,
                price,
                side,
                snapshots,
                product_timestamps,
                horizon,
            )
        enriched_fills.append(enriched)

    stats_by_arm: dict[str, dict[str, Any]] = {}
    if summary_events:
        latest = summary_events[-1]
        raw_stats = latest.get("stats", {})
        if isinstance(raw_stats, dict):
            for arm, values in raw_stats.items():
                if not isinstance(values, dict):
                    continue
                stats_by_arm[str(arm)] = {
                    "posted_count": int(values.get("posted_count", 0) or 0),
                    "posted_qty": int(values.get("posted_qty", 0) or 0),
                    "filled_count_summary": int(values.get("filled_count", 0) or 0),
                    "filled_qty_summary": int(values.get("filled_qty", 0) or 0),
                }

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in enriched_fills:
        grouped[str(row.get("arm", ""))].append(row)

    arm_rows: list[dict[str, Any]] = []
    for arm in sorted(set(stats_by_arm) | set(grouped)):
        fills = grouped.get(arm, [])
        posted = stats_by_arm.get(arm, {})
        arm_rows.append(
            {
                "arm": arm,
                "side": arm.split("_")[0] if "_" in arm else None,
                "distance": int(arm.split("d")[-1]) if "d" in arm else None,
                "posted_count": posted.get("posted_count", 0),
                "posted_qty": posted.get("posted_qty", 0),
                "filled_count": len(fills),
                "filled_qty": sum(int(row.get("qty", 0)) for row in fills),
                "fill_rate_count": (
                    len(fills) / posted.get("posted_count", 1)
                    if posted.get("posted_count", 0) > 0
                    else None
                ),
                "avg_age_steps": safe_avg([float(row.get("age_steps", 0)) for row in fills]),
                "avg_visible_edge_fill": safe_avg(
                    [float(row["visible_edge_fill"]) for row in fills if row.get("visible_edge_fill") is not None]
                ),
                "avg_markout_1": safe_avg([float(row["markout_1"]) for row in fills if row.get("markout_1") is not None]),
                "avg_markout_4": safe_avg([float(row["markout_4"]) for row in fills if row.get("markout_4") is not None]),
                "avg_markout_8": safe_avg([float(row["markout_8"]) for row in fills if row.get("markout_8") is not None]),
            }
        )

    write_csv(output_dir / "ladder_fill_events.csv", enriched_fills)
    write_csv(output_dir / "ladder_arm_summary.csv", arm_rows)
    (output_dir / "ladder_events.json").write_text(json.dumps(events, indent=2) + "\n")

    lines = [
        "Passive Ladder Probe Summary",
        "============================",
        f"Log file: {log_path}",
        f"Json file: {json_path}",
        f"Total ladder events: {len(events)}",
        f"Fill events: {len(fill_events)}",
        f"Summary events: {len(summary_events)}",
        "",
        "Arm summary:",
    ]
    for row in arm_rows:
        lines.append(
            "- "
            + f"{row['arm']}: posted_count={row['posted_count']} filled_count={row['filled_count']} "
            + f"fill_rate={row['fill_rate_count']} avg_age={row['avg_age_steps']} "
            + f"avg_edge_fill={row['avg_visible_edge_fill']} avg_m4={row['avg_markout_4']}"
        )

    if enriched_fills:
        lines.extend(["", "Sample fills:"])
        for row in enriched_fills[:12]:
            lines.append(
                "- "
                + f"{row['fill_ts']} {row['arm']} {row['side']} px={row['price']} qty={row['qty']} "
                + f"age={row['age_steps']} edge_fill={row['visible_edge_fill']} "
                + f"m1={row['markout_1']} m4={row['markout_4']} m8={row['markout_8']}"
            )

    summary_path = output_dir / "summary.txt"
    summary_path.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
