from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ConversionReference:
    import_cost: float
    export_value: float
    fair_value: float


def conversion_reference_prices(
    *,
    bid_price: float,
    ask_price: float,
    transport_fees: float,
    export_tariff: float,
    import_tariff: float,
    extra_fee: float = 0.0,
) -> ConversionReference:
    import_cost = float(ask_price) + float(transport_fees) + float(import_tariff) + float(extra_fee)
    export_value = float(bid_price) - float(transport_fees) - float(export_tariff) - float(extra_fee)
    fair_value = (import_cost + export_value) / 2.0
    return ConversionReference(import_cost=import_cost, export_value=export_value, fair_value=fair_value)


def conversion_edges(
    *,
    local_best_bid: float,
    local_best_ask: float,
    reference: ConversionReference,
) -> tuple[float, float]:
    buy_and_export_edge = reference.export_value - float(local_best_ask)
    import_and_sell_edge = float(local_best_bid) - reference.import_cost
    return buy_and_export_edge, import_and_sell_edge
