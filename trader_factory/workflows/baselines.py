from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from trader_factory.core.paths import ensure_dir, trader_factory_root


def _relative_to_repo(path: Path) -> str:
    repo_root = trader_factory_root()
    try:
        return str(path.resolve().relative_to(repo_root))
    except ValueError:
        return str(path.resolve())


def _resolve_path(value: str | None) -> Path | None:
    if not value:
        return None
    raw = Path(value).expanduser()
    if raw.is_absolute():
        return raw.resolve()
    return (trader_factory_root() / raw).resolve()


@dataclass(slots=True)
class ImcBaselinePolicy:
    round_id: int
    compare_bot_path: Path | None = None
    official_baseline_log: Path | None = None
    official_baseline_json: Path | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_id": self.round_id,
            "compare_bot_path": _relative_to_repo(self.compare_bot_path) if self.compare_bot_path else None,
            "official_baseline_log": _relative_to_repo(self.official_baseline_log) if self.official_baseline_log else None,
            "official_baseline_json": _relative_to_repo(self.official_baseline_json) if self.official_baseline_json else None,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImcBaselinePolicy":
        return cls(
            round_id=int(data["round_id"]),
            compare_bot_path=_resolve_path(data.get("compare_bot_path")),
            official_baseline_log=_resolve_path(data.get("official_baseline_log")),
            official_baseline_json=_resolve_path(data.get("official_baseline_json")),
            notes=str(data.get("notes", "")).strip(),
        )


def baseline_policy_dir() -> Path:
    return trader_factory_root() / "configs" / "baselines"


def baseline_policy_path(round_id: int) -> Path:
    return baseline_policy_dir() / f"imc_round_{round_id}.json"


def load_imc_baseline_policy(round_id: int) -> ImcBaselinePolicy | None:
    path = baseline_policy_path(round_id)
    if not path.exists():
        return None
    payload = json.loads(path.read_text())
    return ImcBaselinePolicy.from_dict(payload)


def save_imc_baseline_policy(policy: ImcBaselinePolicy) -> Path:
    path = baseline_policy_path(policy.round_id)
    ensure_dir(path.parent)
    path.write_text(json.dumps(policy.to_dict(), indent=2) + "\n")
    return path


def set_imc_baseline_policy(
    *,
    round_id: int,
    compare_bot_path: str | Path | None = None,
    official_baseline_log: str | Path | None = None,
    official_baseline_json: str | Path | None = None,
    notes: str = "",
) -> tuple[ImcBaselinePolicy, Path]:
    existing = load_imc_baseline_policy(round_id) or ImcBaselinePolicy(round_id=round_id)
    policy = ImcBaselinePolicy(
        round_id=round_id,
        compare_bot_path=Path(compare_bot_path).expanduser().resolve() if compare_bot_path is not None else existing.compare_bot_path,
        official_baseline_log=(
            Path(official_baseline_log).expanduser().resolve()
            if official_baseline_log is not None
            else existing.official_baseline_log
        ),
        official_baseline_json=(
            Path(official_baseline_json).expanduser().resolve()
            if official_baseline_json is not None
            else existing.official_baseline_json
        ),
        notes=notes if notes else existing.notes,
    )
    path = save_imc_baseline_policy(policy)
    return policy, path


def describe_imc_baseline_policy(policy: ImcBaselinePolicy | None) -> str:
    if policy is None:
        return "No IMC baseline policy configured."
    lines = [
        f"round_id: {policy.round_id}",
        f"compare_bot_path: {policy.compare_bot_path}",
        f"official_baseline_log: {policy.official_baseline_log}",
        f"official_baseline_json: {policy.official_baseline_json}",
        f"notes: {policy.notes or ''}",
    ]
    return "\n".join(lines)
