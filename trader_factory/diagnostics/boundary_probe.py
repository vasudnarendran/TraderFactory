#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize boundary-probe DIAG events from an official submission log.")
    parser.add_argument("log_path", type=Path, help="Path to the official .log JSON file")
    parser.add_argument(
        "--output",
        default="",
        help="Optional output directory. Defaults to generated/reports/boundary_probe/<log_stem>/",
    )
    return parser.parse_args()


def load_log(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict JSON in {path}")
    return data


def extract_boundary_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
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
                    if not event_type.startswith("bd_"):
                        continue
                    item = dict(event)
                    item["_log_timestamp"] = timestamp
                    item["_log_field"] = field
                    events.append(item)
    events.sort(key=lambda row: (int(row.get("ts", 0)), str(row.get("et", ""))))
    return events


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


def render_event(row: dict[str, Any]) -> str:
    changed = row.get("chg", [])
    return (
        f"{row.get('ts')} {row.get('et')} changes={changed} "
        f"bg={row.get('bg')} sg={row.get('sg')} pos={row.get('pos')} tp={row.get('tp')} "
        f"buy_quote {row.get('buy_quote_base')}->{row.get('buy_quote_shadow')} "
        f"sell_quote {row.get('sell_quote_base')}->{row.get('sell_quote_shadow')} "
        f"buy_passive {row.get('buy_passive_base')}->{row.get('buy_passive_shadow')} "
        f"sell_passive {row.get('sell_passive_base')}->{row.get('sell_passive_shadow')}"
    )


def main() -> None:
    args = parse_args()
    log_path = args.log_path.expanduser().resolve()
    payload = load_log(log_path)

    output_dir = (
        Path(args.output).expanduser().resolve()
        if args.output
        else (Path(__file__).resolve().parents[2] / "generated" / "reports" / "boundary_probe" / log_path.stem)
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    events = extract_boundary_events(payload)
    write_csv(output_dir / "boundary_events.csv", events)
    (output_dir / "boundary_events.json").write_text(json.dumps(events, indent=2) + "\n")

    type_counts = Counter(str(row.get("et", "")) for row in events)
    changed_field_counts = Counter()
    max_buy_guard = 0.0
    max_sell_guard = 0.0
    summary_rows: list[dict[str, Any]] = []
    for row in events:
        max_buy_guard = max(max_buy_guard, float(row.get("bg", 0.0) or 0.0), float(row.get("max_buy_guard", 0.0) or 0.0))
        max_sell_guard = max(max_sell_guard, float(row.get("sg", 0.0) or 0.0), float(row.get("max_sell_guard", 0.0) or 0.0))
        for field in row.get("chg", []) or []:
            changed_field_counts[str(field)] += 1
        if row.get("et") == "bd_summary":
            summary_rows.append(row)

    first_change = next((row for row in events if row.get("et") == "bd_change"), None)
    change_events = [row for row in events if row.get("et") == "bd_change"]
    guard_events = [row for row in events if row.get("et") == "bd_guard"]
    live_overlay = len(change_events) > 0

    lines = [
        "Boundary Probe Summary",
        "======================",
        f"Log file: {log_path}",
        f"Extracted boundary events: {len(events)}",
        f"Live overlay: {live_overlay}",
        f"bd_change events: {len(change_events)}",
        f"bd_guard events: {len(guard_events)}",
        f"bd_summary events: {len(summary_rows)}",
        f"Max buy guard observed: {max_buy_guard:.4f}",
        f"Max sell guard observed: {max_sell_guard:.4f}",
        "",
        "Event counts:",
    ]
    for key, count in type_counts.items():
        lines.append(f"- {key}: {count}")

    if changed_field_counts:
        lines.extend(["", "Changed field counts:"])
        for field, count in changed_field_counts.most_common():
            lines.append(f"- {field}: {count}")

    if summary_rows:
        lines.extend(["", "Summary events:"])
        for row in summary_rows:
            lines.append(
                "- "
                + f"ts={row.get('ts')} active_ticks={row.get('active_ticks')} changed_ticks={row.get('changed_ticks')} "
                + f"max_buy_guard={row.get('max_buy_guard')} max_sell_guard={row.get('max_sell_guard')} "
                + f"change_counts={row.get('change_counts')}"
            )

    if first_change:
        lines.extend(["", "First discrete change event:"])
        lines.append(f"- {render_event(first_change)}")

    if change_events:
        lines.extend(["", "Sample change events:"])
        for row in change_events[:8]:
            lines.append(f"- {render_event(row)}")

    summary_path = output_dir / "summary.txt"
    summary_path.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
