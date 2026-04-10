from __future__ import annotations

from enum import Enum


class WorkflowMode(str, Enum):
    DEVELOP = "develop"
    RESEARCH = "research"


def workflow_summary() -> dict[str, list[str]]:
    return {
        WorkflowMode.DEVELOP.value: [
            "Build a production candidate from validated ideas.",
            "Run deterministic replay and Monte Carlo robustness checks.",
            "Use CMA-ES or targeted sweeps only when the logic is trusted.",
            "Promote the best validated candidate into the active competition repo.",
        ],
        WorkflowMode.RESEARCH.value: [
            "Use probes and diagnostics when local and official disagree.",
            "Measure execution behavior and decision-boundary liveness.",
            "Record discoveries in durable docs before changing production logic.",
            "Switch back to develop mode only after a probe yields a usable edge.",
        ],
    }

