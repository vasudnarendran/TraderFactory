"""Simulation adapters live here."""

from typing import TYPE_CHECKING, Any

from trader_factory.simulation.deterministic import DeterministicRunResult, run_deterministic

if TYPE_CHECKING:
    from trader_factory.simulation.monte_carlo import MonteCarloRunResult


def run_monte_carlo(*args: Any, **kwargs: Any):
    from trader_factory.simulation.monte_carlo import run_monte_carlo as _run_monte_carlo

    return _run_monte_carlo(*args, **kwargs)


__all__ = [
    "DeterministicRunResult",
    "run_deterministic",
    "run_monte_carlo",
    "MonteCarloRunResult",
]
