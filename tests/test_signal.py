from trader_factory.strategies.signal import signal_reference_fair


def test_signal_reference_fair_centers_scales_and_shifts_base_fair() -> None:
    reference = signal_reference_fair(
        base_fair=100.0,
        signal_value=12.0,
        baseline=10.0,
        signal_scale=2.0,
        signal_weight=1.5,
        tick_size=1.0,
    )

    assert reference.raw_value == 12.0
    assert reference.centered_signal == 1.0
    assert reference.clipped_signal == 1.0
    assert reference.fair_shift == 1.5
    assert reference.fair_value == 101.5


def test_signal_reference_fair_clips_large_signal_values() -> None:
    reference = signal_reference_fair(
        base_fair=100.0,
        signal_value=20.0,
        baseline=10.0,
        signal_scale=2.0,
        signal_weight=1.0,
        tick_size=2.0,
        max_abs_signal=3.0,
    )

    assert reference.centered_signal == 5.0
    assert reference.clipped_signal == 3.0
    assert reference.fair_shift == 6.0
    assert reference.fair_value == 106.0
