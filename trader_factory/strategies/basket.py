from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(slots=True)
class BasketComponent:
    symbol: str
    weight: float = 1.0
    offset: float = 0.0


def normalize_basket_components(component_specs: Sequence[Mapping[str, object]] | None = None) -> list[BasketComponent]:
    components: list[BasketComponent] = []
    for spec in component_specs or []:
        symbol = str(spec.get("symbol", spec.get("counterpart", ""))).strip()
        if not symbol:
            continue
        raw_weight = spec.get("weight", spec.get("hedge_ratio", 1.0))
        raw_offset = spec.get("offset", 0.0)
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError):
            weight = 1.0
        try:
            offset = float(raw_offset)
        except (TypeError, ValueError):
            offset = 0.0
        components.append(BasketComponent(symbol=symbol, weight=weight, offset=offset))
    return components


def basket_reference_fair(
    *,
    component_mid_prices: Mapping[str, float | None],
    component_specs: Sequence[Mapping[str, object]] | None = None,
    basket_divisor: float = 1.0,
    fair_offset: float = 0.0,
) -> float | None:
    components = normalize_basket_components(component_specs)
    if not components:
        return None

    synthetic_total = 0.0
    for component in components:
        mid_price = component_mid_prices.get(component.symbol)
        if mid_price is None:
            return None
        synthetic_total += float(mid_price) * component.weight + component.offset

    try:
        divisor = float(basket_divisor)
    except (TypeError, ValueError):
        divisor = 1.0
    if divisor == 0.0:
        divisor = 1.0
    return synthetic_total / divisor + float(fair_offset)
