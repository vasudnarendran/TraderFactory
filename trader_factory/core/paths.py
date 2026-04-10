from __future__ import annotations

from pathlib import Path


def trader_factory_root() -> Path:
    return Path(__file__).resolve().parents[2]


def prosperity_root() -> Path:
    return trader_factory_root().parent / "Prosperity"


def generated_root() -> Path:
    return trader_factory_root() / "generated"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def legacy_backtest_script() -> Path:
    return prosperity_root() / "Backtest_failed_Python" / "run_backtest.py"


def legacy_monte_carlo_root() -> Path:
    return prosperity_root() / "MonteCarloBacktester"


def legacy_analysis_script(script_name: str) -> Path:
    return prosperity_root() / "Analysis" / script_name


def legacy_analysis_output_dir() -> Path:
    return prosperity_root() / "Analysis" / "output"


def internal_backtest_script() -> Path:
    return trader_factory_root() / "trader_factory" / "simulation" / "internal_backtest.py"


def internal_diagnostic_script(script_name: str) -> Path:
    return trader_factory_root() / "trader_factory" / "diagnostics" / script_name
