from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from trader_factory.core.paths import ensure_dir, generated_root, internal_backtest_script, trader_factory_root


FINAL_TOTAL_RE = re.compile(r"Final total PnL:\s*([-+]?\d+(?:\.\d+)?)")


@dataclass(slots=True)
class DeterministicRunResult:
    bot_path: Path
    day: int
    output_dir: Path
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    summary_path: Path
    step_log_path: Path
    fills_path: Path
    product_log_path: Path
    final_total_pnl: float | None


def default_output_dir(bot_path: Path, day: int) -> Path:
    return ensure_dir(generated_root() / "runs" / "deterministic" / f"{bot_path.stem}_day_{day}")


def parse_final_total_pnl(summary_path: Path, stdout: str) -> float | None:
    text = summary_path.read_text() if summary_path.exists() else stdout
    match = FINAL_TOTAL_RE.search(text)
    if match is None:
        return None
    return float(match.group(1))


def run_deterministic(
    bot_path: str | Path,
    *,
    day: int = -1,
    output_dir: str | Path | None = None,
    python_bin: str = sys.executable,
    timeout_seconds: float | None = None,
    check: bool = True,
) -> DeterministicRunResult:
    bot = Path(bot_path).expanduser().resolve()
    out_dir = Path(output_dir).expanduser().resolve() if output_dir else default_output_dir(bot, day)
    ensure_dir(out_dir)

    command = [
        python_bin,
        str(internal_backtest_script()),
        str(bot),
        "--day",
        str(day),
        "--output",
        str(out_dir),
    ]
    process = subprocess.run(
        command,
        cwd=trader_factory_root(),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if check and process.returncode != 0:
        raise RuntimeError(process.stderr.strip() or process.stdout.strip() or "Deterministic run failed")

    summary_path = out_dir / "summary.txt"
    result = DeterministicRunResult(
        bot_path=bot,
        day=day,
        output_dir=out_dir,
        command=command,
        returncode=process.returncode,
        stdout=process.stdout,
        stderr=process.stderr,
        summary_path=summary_path,
        step_log_path=out_dir / "step_log.csv",
        fills_path=out_dir / "fills.csv",
        product_log_path=out_dir / "product_log.csv",
        final_total_pnl=parse_final_total_pnl(summary_path, process.stdout),
    )
    return result
