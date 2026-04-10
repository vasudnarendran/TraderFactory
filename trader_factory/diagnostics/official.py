from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from trader_factory.core.paths import (
    ensure_dir,
    generated_root,
    internal_diagnostic_script,
    trader_factory_root,
)


@dataclass(slots=True)
class DiagnosticRunResult:
    name: str
    output_dir: Path
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    summary_path: Path | None = None


def _default_reports_dir(group: str, stem: str) -> Path:
    return ensure_dir(generated_root() / "reports" / group / stem)


def _run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        command,
        cwd=trader_factory_root(),
        capture_output=True,
        text=True,
    )
    if check and process.returncode != 0:
        raise RuntimeError(process.stderr.strip() or process.stdout.strip() or "Diagnostic run failed")
    return process


def run_official_trade_quality(
    log_path: str | Path,
    *,
    baseline_log: str | Path | None = None,
    primary_json: str | Path | None = None,
    baseline_json: str | Path | None = None,
    output_dir: str | Path | None = None,
    output_prefix: str = "",
    python_bin: str = sys.executable,
    check: bool = True,
) -> DiagnosticRunResult:
    log = Path(log_path).expanduser().resolve()
    baseline = Path(baseline_log).expanduser().resolve() if baseline_log else None
    prefix = output_prefix or (f"{baseline.stem}_vs_{log.stem}" if baseline else log.stem)
    target_dir = Path(output_dir).expanduser().resolve() if output_dir else _default_reports_dir("official_trade_quality", prefix)
    ensure_dir(target_dir)
    command = [
        python_bin,
        str(internal_diagnostic_script("trade_quality.py")),
        str(log),
        "--output-dir",
        str(target_dir),
    ]
    if baseline is not None:
        command.extend(["--baseline", str(baseline)])
    if primary_json is not None:
        command.extend(["--primary-json", str(Path(primary_json).expanduser().resolve())])
    if baseline_json is not None:
        command.extend(["--baseline-json", str(Path(baseline_json).expanduser().resolve())])
    command.extend(["--output-prefix", prefix])

    process = _run(command, check=check)
    copied_summary = target_dir / f"{prefix}_official_trade_quality_report.md"
    if not copied_summary.exists():
        copied_summary = None

    return DiagnosticRunResult(
        name="official_trade_quality",
        output_dir=target_dir,
        command=command,
        returncode=process.returncode,
        stdout=process.stdout,
        stderr=process.stderr,
        summary_path=copied_summary,
    )


def run_boundary_probe_report(
    log_path: str | Path,
    *,
    output_dir: str | Path | None = None,
    python_bin: str = sys.executable,
    check: bool = True,
) -> DiagnosticRunResult:
    log = Path(log_path).expanduser().resolve()
    out = Path(output_dir).expanduser().resolve() if output_dir else _default_reports_dir("boundary_probe", log.stem)
    ensure_dir(out)
    command = [
        python_bin,
        str(internal_diagnostic_script("boundary_probe.py")),
        str(log),
        "--output",
        str(out),
    ]
    process = _run(command, check=check)
    return DiagnosticRunResult(
        name="boundary_probe",
        output_dir=out,
        command=command,
        returncode=process.returncode,
        stdout=process.stdout,
        stderr=process.stderr,
        summary_path=out / "summary.txt",
    )


def run_passive_ladder_report(
    log_path: str | Path,
    *,
    json_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    python_bin: str = sys.executable,
    check: bool = True,
) -> DiagnosticRunResult:
    log = Path(log_path).expanduser().resolve()
    out = Path(output_dir).expanduser().resolve() if output_dir else _default_reports_dir("passive_ladder", log.stem)
    ensure_dir(out)
    command = [
        python_bin,
        str(internal_diagnostic_script("passive_ladder.py")),
        str(log),
        "--output",
        str(out),
    ]
    if json_path is not None:
        command.extend(["--json-path", str(Path(json_path).expanduser().resolve())])
    process = _run(command, check=check)
    return DiagnosticRunResult(
        name="passive_ladder",
        output_dir=out,
        command=command,
        returncode=process.returncode,
        stdout=process.stdout,
        stderr=process.stderr,
        summary_path=out / "summary.txt",
    )


def run_aggressive_markout_report(
    log_path: str | Path,
    *,
    json_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    python_bin: str = sys.executable,
    check: bool = True,
) -> DiagnosticRunResult:
    log = Path(log_path).expanduser().resolve()
    out = Path(output_dir).expanduser().resolve() if output_dir else _default_reports_dir("aggressive_markout", log.stem)
    ensure_dir(out)
    command = [
        python_bin,
        str(internal_diagnostic_script("aggressive_markout.py")),
        str(log),
        "--output",
        str(out),
    ]
    if json_path is not None:
        command.extend(["--json-path", str(Path(json_path).expanduser().resolve())])
    process = _run(command, check=check)
    return DiagnosticRunResult(
        name="aggressive_markout",
        output_dir=out,
        command=command,
        returncode=process.returncode,
        stdout=process.stdout,
        stderr=process.stderr,
        summary_path=out / "summary.txt",
    )
