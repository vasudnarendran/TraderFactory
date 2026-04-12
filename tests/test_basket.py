from trader_factory.strategies.basket import basket_reference_fair


def test_basket_reference_fair_returns_weighted_synthetic_value() -> None:
    fair = basket_reference_fair(
        component_mid_prices={"A": 100.0, "B": 40.0},
        component_specs=[
            {"symbol": "A", "weight": 2.0},
            {"symbol": "B", "weight": -1.0},
        ],
        basket_divisor=1.0,
        fair_offset=3.0,
    )

    assert fair == 163.0


def test_basket_reference_fair_requires_all_component_prices() -> None:
    fair = basket_reference_fair(
        component_mid_prices={"A": 100.0},
        component_specs=[
            {"symbol": "A", "weight": 1.0},
            {"symbol": "B", "weight": 1.0},
        ],
    )

    assert fair is None
