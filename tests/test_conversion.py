from trader_factory.strategies.conversion import conversion_edges, conversion_reference_prices


def test_conversion_reference_prices_build_import_export_band() -> None:
    reference = conversion_reference_prices(
        bid_price=105.0,
        ask_price=95.0,
        transport_fees=2.0,
        export_tariff=1.0,
        import_tariff=3.0,
        extra_fee=0.5,
    )
    assert reference.import_cost == 100.5
    assert reference.export_value == 101.5
    assert reference.fair_value == 101.0


def test_conversion_edges_measure_buy_export_and_import_sell_opportunities() -> None:
    reference = conversion_reference_prices(
        bid_price=105.0,
        ask_price=95.0,
        transport_fees=2.0,
        export_tariff=1.0,
        import_tariff=3.0,
    )
    buy_export_edge, import_sell_edge = conversion_edges(
        local_best_bid=103.0,
        local_best_ask=99.0,
        reference=reference,
    )
    assert buy_export_edge == 3.0
    assert import_sell_edge == 3.0
