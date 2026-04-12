from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trader_factory.core.paths import ensure_dir, trader_factory_root


@dataclass(slots=True)
class ImcGatePolicy:
    round_id: int
    require_deterministic: bool = True
    require_monte_carlo: bool = True
    deterministic_min_total_delta: float | None = 0.0
    mc_min_mean_delta: float | None = 0.0
    mc_min_p10_delta: float | None = None
    mc_min_plausible_mean_delta: float | None = 0.0
    mc_min_plausible_p10_delta: float | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_id": self.round_id,
            "require_deterministic": self.require_deterministic,
            "require_monte_carlo": self.require_monte_carlo,
            "deterministic_min_total_delta": self.deterministic_min_total_delta,
            "mc_min_mean_delta": self.mc_min_mean_delta,
            "mc_min_p10_delta": self.mc_min_p10_delta,
            "mc_min_plausible_mean_delta": self.mc_min_plausible_mean_delta,
            "mc_min_plausible_p10_delta": self.mc_min_plausible_p10_delta,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImcGatePolicy":
        return cls(
            round_id=int(data["round_id"]),
            require_deterministic=bool(data.get("require_deterministic", True)),
            require_monte_carlo=bool(data.get("require_monte_carlo", True)),
            deterministic_min_total_delta=(
                None if data.get("deterministic_min_total_delta") is None else float(data["deterministic_min_total_delta"])
            ),
            mc_min_mean_delta=None if data.get("mc_min_mean_delta") is None else float(data["mc_min_mean_delta"]),
            mc_min_p10_delta=None if data.get("mc_min_p10_delta") is None else float(data["mc_min_p10_delta"]),
            mc_min_plausible_mean_delta=(
                None if data.get("mc_min_plausible_mean_delta") is None else float(data["mc_min_plausible_mean_delta"])
            ),
            mc_min_plausible_p10_delta=(
                None if data.get("mc_min_plausible_p10_delta") is None else float(data["mc_min_plausible_p10_delta"])
            ),
            notes=str(data.get("notes", "")).strip(),
        )


DEFAULT_IMC_GATE_POLICY = ImcGatePolicy(round_id=0)


@dataclass(slots=True)
class GateCheck:
    name: str
    passed: bool
    actual: float | None = None
    min_required: float | None = None
    required: bool = True
    reason: str = ""


@dataclass(slots=True)
class ImcGateEvaluation:
    policy: ImcGatePolicy
    checks: list[GateCheck]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks if check.required)


def gate_policy_dir() -> Path:
    return trader_factory_root() / "configs" / "gates"


def gate_policy_path(round_id: int) -> Path:
    return gate_policy_dir() / f"imc_round_{round_id}.json"


def load_imc_gate_policy(round_id: int) -> ImcGatePolicy | None:
    path = gate_policy_path(round_id)
    if not path.exists():
        return None
    return ImcGatePolicy.from_dict(json.loads(path.read_text()))


def save_imc_gate_policy(policy: ImcGatePolicy) -> Path:
    path = gate_policy_path(policy.round_id)
    ensure_dir(path.parent)
    path.write_text(json.dumps(policy.to_dict(), indent=2) + "\n")
    return path


def set_imc_gate_policy(
    *,
    round_id: int,
    require_deterministic: bool | None = None,
    require_monte_carlo: bool | None = None,
    deterministic_min_total_delta: float | None = None,
    mc_min_mean_delta: float | None = None,
    mc_min_p10_delta: float | None = None,
    mc_min_plausible_mean_delta: float | None = None,
    mc_min_plausible_p10_delta: float | None = None,
    notes: str = "",
) -> tuple[ImcGatePolicy, Path]:
    existing = load_imc_gate_policy(round_id) or ImcGatePolicy(round_id=round_id)
    policy = ImcGatePolicy(
        round_id=round_id,
        require_deterministic=existing.require_deterministic if require_deterministic is None else require_deterministic,
        require_monte_carlo=existing.require_monte_carlo if require_monte_carlo is None else require_monte_carlo,
        deterministic_min_total_delta=(
            existing.deterministic_min_total_delta
            if deterministic_min_total_delta is None
            else deterministic_min_total_delta
        ),
        mc_min_mean_delta=existing.mc_min_mean_delta if mc_min_mean_delta is None else mc_min_mean_delta,
        mc_min_p10_delta=existing.mc_min_p10_delta if mc_min_p10_delta is None else mc_min_p10_delta,
        mc_min_plausible_mean_delta=(
            existing.mc_min_plausible_mean_delta
            if mc_min_plausible_mean_delta is None
            else mc_min_plausible_mean_delta
        ),
        mc_min_plausible_p10_delta=(
            existing.mc_min_plausible_p10_delta
            if mc_min_plausible_p10_delta is None
            else mc_min_plausible_p10_delta
        ),
        notes=notes if notes else existing.notes,
    )
    path = save_imc_gate_policy(policy)
    return policy, path


def describe_imc_gate_policy(policy: ImcGatePolicy | None) -> str:
    if policy is None:
        return "No IMC gate policy configured."
    lines = [
        f"round_id: {policy.round_id}",
        f"require_deterministic: {policy.require_deterministic}",
        f"require_monte_carlo: {policy.require_monte_carlo}",
        f"deterministic_min_total_delta: {policy.deterministic_min_total_delta}",
        f"mc_min_mean_delta: {policy.mc_min_mean_delta}",
        f"mc_min_p10_delta: {policy.mc_min_p10_delta}",
        f"mc_min_plausible_mean_delta: {policy.mc_min_plausible_mean_delta}",
        f"mc_min_plausible_p10_delta: {policy.mc_min_plausible_p10_delta}",
        f"notes: {policy.notes or ''}",
    ]
    return "\n".join(lines)


def resolve_imc_gate_policy(
    *,
    round_id: int,
    base_policy: ImcGatePolicy | None = None,
    require_deterministic: bool | None = None,
    require_monte_carlo: bool | None = None,
    deterministic_min_total_delta: float | None = None,
    mc_min_mean_delta: float | None = None,
    mc_min_p10_delta: float | None = None,
    mc_min_plausible_mean_delta: float | None = None,
    mc_min_plausible_p10_delta: float | None = None,
) -> ImcGatePolicy:
    base = base_policy or ImcGatePolicy(
        round_id=round_id,
        require_deterministic=DEFAULT_IMC_GATE_POLICY.require_deterministic,
        require_monte_carlo=DEFAULT_IMC_GATE_POLICY.require_monte_carlo,
        deterministic_min_total_delta=DEFAULT_IMC_GATE_POLICY.deterministic_min_total_delta,
        mc_min_mean_delta=DEFAULT_IMC_GATE_POLICY.mc_min_mean_delta,
        mc_min_p10_delta=DEFAULT_IMC_GATE_POLICY.mc_min_p10_delta,
        mc_min_plausible_mean_delta=DEFAULT_IMC_GATE_POLICY.mc_min_plausible_mean_delta,
        mc_min_plausible_p10_delta=DEFAULT_IMC_GATE_POLICY.mc_min_plausible_p10_delta,
        notes="",
    )
    return ImcGatePolicy(
        round_id=round_id,
        require_deterministic=base.require_deterministic if require_deterministic is None else require_deterministic,
        require_monte_carlo=base.require_monte_carlo if require_monte_carlo is None else require_monte_carlo,
        deterministic_min_total_delta=(
            base.deterministic_min_total_delta
            if deterministic_min_total_delta is None
            else deterministic_min_total_delta
        ),
        mc_min_mean_delta=base.mc_min_mean_delta if mc_min_mean_delta is None else mc_min_mean_delta,
        mc_min_p10_delta=base.mc_min_p10_delta if mc_min_p10_delta is None else mc_min_p10_delta,
        mc_min_plausible_mean_delta=(
            base.mc_min_plausible_mean_delta
            if mc_min_plausible_mean_delta is None
            else mc_min_plausible_mean_delta
        ),
        mc_min_plausible_p10_delta=(
            base.mc_min_plausible_p10_delta
            if mc_min_plausible_p10_delta is None
            else mc_min_plausible_p10_delta
        ),
        notes=base.notes,
    )


def _threshold_check(name: str, actual: float | None, minimum: float | None) -> GateCheck:
    if minimum is None:
        return GateCheck(name=name, passed=True, actual=actual, min_required=None, reason="No minimum threshold configured.")
    if actual is None:
        return GateCheck(name=name, passed=False, actual=None, min_required=minimum, reason="Metric unavailable.")
    passed = float(actual) >= minimum
    return GateCheck(
        name=name,
        passed=passed,
        actual=float(actual),
        min_required=minimum,
        reason="Passed." if passed else f"Expected at least {minimum}, got {actual}.",
    )


def evaluate_imc_gate_policy(
    *,
    policy: ImcGatePolicy,
    deterministic_ran: bool,
    deterministic_total_delta: float | None,
    monte_carlo_ran: bool,
    mc_mean_delta: float | None,
    mc_p10_delta: float | None,
    mc_plausible_mean_delta: float | None,
    mc_plausible_p10_delta: float | None,
) -> ImcGateEvaluation:
    checks: list[GateCheck] = []
    if policy.require_deterministic:
        if not deterministic_ran:
            checks.append(
                GateCheck(
                    name="deterministic_ran",
                    passed=False,
                    required=True,
                    reason="Deterministic gate is required by policy but did not run.",
                )
            )
        else:
            checks.append(_threshold_check("deterministic_total_delta", deterministic_total_delta, policy.deterministic_min_total_delta))
    if policy.require_monte_carlo:
        if not monte_carlo_ran:
            checks.append(
                GateCheck(
                    name="monte_carlo_ran",
                    passed=False,
                    required=True,
                    reason="Monte Carlo gate is required by policy but did not run.",
                )
            )
        else:
            checks.append(_threshold_check("mc_mean_delta", mc_mean_delta, policy.mc_min_mean_delta))
            checks.append(_threshold_check("mc_p10_delta", mc_p10_delta, policy.mc_min_p10_delta))
            checks.append(
                _threshold_check("mc_plausible_mean_delta", mc_plausible_mean_delta, policy.mc_min_plausible_mean_delta)
            )
            checks.append(
                _threshold_check("mc_plausible_p10_delta", mc_plausible_p10_delta, policy.mc_min_plausible_p10_delta)
            )
    return ImcGateEvaluation(policy=policy, checks=checks)
