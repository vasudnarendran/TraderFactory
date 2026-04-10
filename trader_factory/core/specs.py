from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


@dataclass(slots=True)
class MechanicSpec:
    name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MechanicSpec":
        return cls(
            name=str(data["name"]).strip(),
            description=str(data.get("description", "")).strip(),
            tags=_normalize_list(data.get("tags")),
        )


@dataclass(slots=True)
class ProductSpec:
    symbol: str
    position_limit: int
    tick_size: float = 1.0
    price_regime: str = "unknown"
    execution_style: str = "mixed"
    mechanics: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProductSpec":
        return cls(
            symbol=str(data["symbol"]).strip(),
            position_limit=int(data["position_limit"]),
            tick_size=float(data.get("tick_size", 1.0)),
            price_regime=str(data.get("price_regime", "unknown")).strip(),
            execution_style=str(data.get("execution_style", "mixed")).strip(),
            mechanics=_normalize_list(data.get("mechanics")),
            observations=_normalize_list(data.get("observations")),
            notes=str(data.get("notes", "")).strip(),
        )


@dataclass(slots=True)
class CompetitionSpec:
    name: str
    round_name: str
    description: str = ""
    mechanics: list[MechanicSpec] = field(default_factory=list)
    products: list[ProductSpec] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    research_goals: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompetitionSpec":
        mechanics = [MechanicSpec.from_dict(item) for item in data.get("mechanics", [])]
        products = [ProductSpec.from_dict(item) for item in data.get("products", [])]
        return cls(
            name=str(data["name"]).strip(),
            round_name=str(data.get("round_name", "")).strip(),
            description=str(data.get("description", "")).strip(),
            mechanics=mechanics,
            products=products,
            constraints=_normalize_list(data.get("constraints")),
            research_goals=_normalize_list(data.get("research_goals")),
        )

    @classmethod
    def from_json(cls, path: str | Path) -> "CompetitionSpec":
        raw = json.loads(Path(path).read_text())
        return cls.from_dict(raw)

