from __future__ import annotations

import argparse
import csv
import json
import mimetypes
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from trader_factory.core.paths import generated_root, trader_factory_root


ROOT = Path(__file__).resolve().parent
INDEX_HTML = ROOT / "monte_carlo_index.html"
REPO_ROOT = trader_factory_root()
DEFAULT_RESULTS_DIRS = [
    generated_root() / "runs" / "monte_carlo",
    generated_root() / "dashboards",
]


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def detect_kind(data: dict[str, Any]) -> str | None:
    if "overall" in data and "meta" in data:
        return "dashboard"
    if {"config", "baseline", "monte_carlo", "comparison"}.issubset(data.keys()):
        return "mc_report"
    return None


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def source_label(results_dir: Path) -> str:
    try:
        rel = results_dir.resolve().relative_to(REPO_ROOT.resolve())
        return str(rel)
    except ValueError:
        return results_dir.name


def path_id(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def display_name(path: Path, kind: str) -> str:
    if kind == "mc_report" and path.name == "report.json":
        return path.parent.name
    return path.name


def stats_block(block: dict[str, Any] | None) -> dict[str, float | None]:
    block = block or {}
    return {
        "mean": safe_float(block.get("mean")),
        "std": safe_float(block.get("std")),
        "min": safe_float(block.get("min")),
        "p05": safe_float(block.get("p05")),
        "p10": safe_float(block.get("p10")),
        "p25": safe_float(block.get("p25")),
        "p50": safe_float(block.get("p50") if block.get("p50") is not None else block.get("median")),
        "median": safe_float(block.get("median")),
        "p75": safe_float(block.get("p75")),
        "p90": safe_float(block.get("p90")),
        "p95": safe_float(block.get("p95")),
        "max": safe_float(block.get("max")),
        "cvar10": safe_float(block.get("cvar10")),
        "positiveRate": safe_float(block.get("positiveRate")),
        "sharpeLike": safe_float(block.get("sharpeLike")),
        "meanConfidenceLow95": safe_float(block.get("meanConfidenceLow95")),
        "meanConfidenceHigh95": safe_float(block.get("meanConfidenceHigh95")),
    }


def summary_from_dashboard(path: Path, data: dict[str, Any], results_root: Path) -> dict[str, Any]:
    overall = data.get("overall", {})
    products = data.get("products", {})
    meta = data.get("meta", {})
    total = overall.get("totalPnl", {})
    emerald = overall.get("emeraldPnl", {})
    tomato = overall.get("tomatoPnl", {})

    return {
        "kind": "dashboard",
        "id": path_id(path),
        "name": path.name,
        "displayName": display_name(path, "dashboard"),
        "stem": path.stem,
        "path": str(path),
        "sourceLabel": source_label(results_root),
        "mtimeMs": int(path.stat().st_mtime_ns // 1_000_000),
        "sizeBytes": int(path.stat().st_size),
        "algorithmPath": meta.get("algorithmPath"),
        "sessionCount": meta.get("sessionCount"),
        "sampleSessions": meta.get("sampleSessions"),
        "total": {
            "mean": safe_float(total.get("mean")),
            "std": safe_float(total.get("std")),
            "p05": safe_float(total.get("p05")),
            "p50": safe_float(total.get("p50")),
            "p95": safe_float(total.get("p95")),
            "min": safe_float(total.get("min")),
            "max": safe_float(total.get("max")),
            "positiveRate": safe_float(total.get("positiveRate")),
            "sharpeLike": safe_float(total.get("sharpeLike")),
            "meanConfidenceLow95": safe_float(total.get("meanConfidenceLow95")),
            "meanConfidenceHigh95": safe_float(total.get("meanConfidenceHigh95")),
        },
        "emerald": {
            "mean": safe_float(emerald.get("mean")),
            "std": safe_float(emerald.get("std")),
            "p05": safe_float(emerald.get("p05")),
            "p50": safe_float(emerald.get("p50")),
            "p95": safe_float(emerald.get("p95")),
        },
        "tomato": {
            "mean": safe_float(tomato.get("mean")),
            "std": safe_float(tomato.get("std")),
            "p05": safe_float(tomato.get("p05")),
            "p50": safe_float(tomato.get("p50")),
            "p95": safe_float(tomato.get("p95")),
        },
        "correlation": safe_float(overall.get("emeraldTomatoCorrelation")),
        "productNames": sorted(products.keys()),
    }


def summary_from_mc_report(path: Path, data: dict[str, Any], results_root: Path) -> dict[str, Any]:
    comparison = data.get("comparison") or {}
    monte_carlo = data.get("monte_carlo") or {}
    baseline = data.get("baseline") or {}
    config = data.get("config") or {}

    primary_bot = comparison.get("primary_bot")
    if primary_bot not in monte_carlo:
        primary_bot = next(iter(monte_carlo.keys()), None)
    compare_bot = comparison.get("compare_bot")
    primary_payload = monte_carlo.get(primary_bot or "", {})
    overall = primary_payload.get("overall", {})
    profiles = primary_payload.get("profiles", {})

    return {
        "kind": "mc_report",
        "id": path_id(path),
        "name": path.name,
        "displayName": display_name(path, "mc_report"),
        "stem": path.parent.name if path.name == "report.json" else path.stem,
        "path": str(path),
        "sourceLabel": source_label(results_root),
        "mtimeMs": int(path.stat().st_mtime_ns // 1_000_000),
        "sizeBytes": int(path.stat().st_size),
        "algorithmPath": next(iter(config.get("bots", [])), None),
        "sessionCount": overall.get("count"),
        "sampleSessions": overall.get("count"),
        "primaryBot": primary_bot,
        "compareBot": compare_bot,
        "baselinePrimary": safe_float((baseline.get(primary_bot or "") or {}).get("combined_total_pnl")),
        "baselineCompare": safe_float((baseline.get(compare_bot or "") or {}).get("combined_total_pnl")),
        "total": stats_block(overall),
        "all": stats_block((profiles.get("all") if isinstance(profiles, dict) else None) or overall),
        "plausible": stats_block((profiles.get("plausible") if isinstance(profiles, dict) else None) or {}),
        "stress": stats_block((profiles.get("stress") if isinstance(profiles, dict) else None) or {}),
        "comparison": {
            "sharedSamples": comparison.get("shared_samples"),
            "meanDelta": safe_float((comparison.get("summary") or {}).get("mean_delta")),
            "medianDelta": safe_float((comparison.get("summary") or {}).get("median_delta")),
            "p10Delta": safe_float((comparison.get("summary") or {}).get("p10_delta")),
            "winRate": safe_float((comparison.get("summary") or {}).get("win_rate")),
        },
        "familyNames": sorted((primary_payload.get("by_family") or {}).keys()),
        "productNames": ["EMERALDS", "TOMATOES"],
    }


def load_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []

    def convert(value: str) -> Any:
        if value == "":
            return None
        try:
            if "." not in value and "e" not in value.lower():
                return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            return value

    try:
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            return [{key: convert(val) for key, val in row.items()} for row in reader]
    except OSError:
        return []


def report_companion_paths(path: Path) -> tuple[Path, Path]:
    if path.name == "report.json":
        return (path.with_name("sample_totals.csv"), path.with_name("day_results.csv"))

    stem = path.stem
    if stem.endswith("_report"):
        prefix = stem[: -len("_report")]
    else:
        prefix = stem
    return (
        path.with_name(f"{prefix}_sample_totals.csv"),
        path.with_name(f"{prefix}_day_results.csv"),
    )


def iter_result_files(results_dirs: list[Path]) -> list[tuple[Path, Path]]:
    discovered: list[tuple[Path, Path]] = []
    seen: set[Path] = set()
    for results_dir in results_dirs:
        if not results_dir.is_dir():
            continue
        for path in sorted(results_dir.rglob("*.json")):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            discovered.append((results_dir, resolved))
    return discovered


def collect_results(results_dirs: list[Path]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for results_root, path in iter_result_files(results_dirs):
        data = read_json(path)
        if data is None:
            continue
        kind = detect_kind(data)
        if kind == "dashboard":
            results.append(summary_from_dashboard(path, data, results_root))
        elif kind == "mc_report":
            results.append(summary_from_mc_report(path, data, results_root))
    results.sort(key=lambda item: item["mtimeMs"], reverse=True)
    return results


def _is_within_results(path: Path, results_dirs: list[Path]) -> bool:
    resolved = path.resolve()
    for results_dir in results_dirs:
        try:
            resolved.relative_to(results_dir.resolve())
            return True
        except ValueError:
            continue
    return False


def detailed_payload(results_dirs: list[Path], item_id: str) -> dict[str, Any] | None:
    candidate = Path(item_id).expanduser()
    path = candidate.resolve() if candidate.is_absolute() else (REPO_ROOT / candidate).resolve()
    if not path.is_file() or not _is_within_results(path, results_dirs):
        return None

    data = read_json(path)
    if data is None:
        return None

    kind = detect_kind(data)
    if kind is None:
        return None
    if kind == "dashboard":
        return {
            "kind": "dashboard",
            "summary": summary_from_dashboard(path, data, path.parent),
            "dashboard": data,
        }

    sample_totals_path, day_results_path = report_companion_paths(path)
    return {
        "kind": "mc_report",
        "summary": summary_from_mc_report(path, data, path.parent if path.name == "report.json" else path.parent),
        "report": data,
        "sampleTotals": load_csv_rows(sample_totals_path),
        "dayResults": load_csv_rows(day_results_path),
        "sampleTotalsPath": str(sample_totals_path) if sample_totals_path.is_file() else None,
        "dayResultsPath": str(day_results_path) if day_results_path.is_file() else None,
    }


class ViewerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, results_dirs: list[Path], **kwargs: Any) -> None:
        self.results_dirs = results_dirs
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/tests":
            self._json_response({"tests": collect_results(self.results_dirs)})
            return
        if parsed.path == "/api/test":
            query = parse_qs(parsed.query)
            item_id = query.get("name", [""])[0]
            payload = detailed_payload(self.results_dirs, item_id)
            if payload is None:
                self.send_error(404, "Result not found")
                return
            self._json_response(payload)
            return
        if parsed.path in {"/", "/index.html"}:
            self._serve_file(INDEX_HTML)
            return
        super().do_GET()

    def _serve_file(self, path: Path) -> None:
        body = path.read_bytes()
        content_type, _ = mimetypes.guess_type(str(path))
        self.send_response(200)
        self.send_header("Content-Type", content_type or "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json_response(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Browse TraderFactory Monte Carlo results and dashboards.")
    parser.add_argument(
        "--results-dir",
        type=Path,
        action="append",
        dest="results_dirs",
        help="Directory root to scan recursively for report JSON files. Can be passed multiple times.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--port", type=int, default=8012, help="Port to bind.")
    return parser


def run_viewer_server(
    *,
    results_dirs: list[Path] | None = None,
    host: str = "127.0.0.1",
    port: int = 8012,
) -> None:
    dirs = [path.resolve() for path in (results_dirs or DEFAULT_RESULTS_DIRS)]

    def handler(*handler_args: Any, **handler_kwargs: Any) -> ViewerHandler:
        return ViewerHandler(*handler_args, results_dirs=dirs, **handler_kwargs)

    server = ThreadingHTTPServer((host, port), handler)
    print(
        f"TraderFactory viewer running at http://{host}:{port} "
        f"for {', '.join(str(path) for path in dirs)}"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    args = build_parser().parse_args()
    run_viewer_server(results_dirs=args.results_dirs, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
