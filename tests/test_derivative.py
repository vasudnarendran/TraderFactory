from trader_factory.strategies.derivative import black_scholes_option_reference


def test_black_scholes_option_reference_returns_reasonable_atm_call() -> None:
    reference = black_scholes_option_reference(
        spot=100.0,
        strike=100.0,
        time_to_expiry_years=1.0,
        volatility=0.2,
        option_kind="call",
    )

    assert round(reference.fair_value, 4) == 7.9656
    assert round(reference.delta, 4) == 0.5398
    assert reference.intrinsic_value == 0.0


def test_black_scholes_option_reference_collapses_to_intrinsic_at_expiry() -> None:
    reference = black_scholes_option_reference(
        spot=95.0,
        strike=100.0,
        time_to_expiry_years=0.0,
        volatility=0.3,
        option_kind="put",
    )

    assert reference.fair_value == 5.0
    assert reference.intrinsic_value == 5.0
    assert reference.delta == -1.0
