from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(slots=True)
class LinkedRelationship:
    counterpart: str
    hedge_ratio: float = 1.0
    offset: float = 0.0


def normalize_relationships(
    *,
    related_symbols: Sequence[str],
    relationship_details: Sequence[Mapping[str, object]] | None = None,
    default_hedge_ratio: float = 1.0,
) -> list[LinkedRelationship]:
    details_by_symbol: dict[str, Mapping[str, object]] = {}
    for detail in relationship_details or []:
        counterpart = str(detail.get("counterpart", "")).strip()
        if counterpart:
            details_by_symbol[counterpart] = detail

    relationships: list[LinkedRelationship] = []
    for symbol in related_symbols:
        detail = details_by_symbol.get(symbol, {})
        raw_ratio = detail.get("hedge_ratio", default_hedge_ratio)
        raw_offset = detail.get("offset", 0.0)
        try:
            hedge_ratio = float(raw_ratio)
        except (TypeError, ValueError):
            hedge_ratio = float(default_hedge_ratio)
        try:
            offset = float(raw_offset)
        except (TypeError, ValueError):
            offset = 0.0
        relationships.append(LinkedRelationship(counterpart=symbol, hedge_ratio=hedge_ratio, offset=offset))
    return relationships


def linked_reference_fair(
    *,
    own_mid: float,
    related_mid_prices: Mapping[str, float | None],
    related_symbols: Sequence[str],
    relationship_details: Sequence[Mapping[str, object]] | None = None,
    default_hedge_ratio: float = 1.0,
    reference_weight: float = 0.75,
    own_weight: float | None = None,
    spread_offset: float = 0.0,
) -> float | None:
    relationships = normalize_relationships(
        related_symbols=related_symbols,
        relationship_details=relationship_details,
        default_hedge_ratio=default_hedge_ratio,
    )
    transformed_prices: list[float] = []
    for relationship in relationships:
        counterpart_mid = related_mid_prices.get(relationship.counterpart)
        if counterpart_mid is None:
            continue
        transformed_prices.append(float(counterpart_mid) * relationship.hedge_ratio + relationship.offset)
    if not transformed_prices:
        return None
    reference_price = sum(transformed_prices) / len(transformed_prices)
    if own_weight is None:
        own_weight = max(0.0, 1.0 - float(reference_weight))
    total_weight = float(reference_weight) + float(own_weight)
    if total_weight <= 0:
        return reference_price + float(spread_offset)
    return (float(reference_weight) * reference_price + float(own_weight) * float(own_mid)) / total_weight + float(spread_offset)
