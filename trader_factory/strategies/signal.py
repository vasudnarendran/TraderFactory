from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SignalReference:
    raw_value: float
    centered_signal: float
    clipped_signal: float
    fair_shift: float
    fair_value: float


def signal_reference_fair(
    *,
    base_fair: float,
    signal_value: float,
    baseline: float = 0.0,
    signal_scale: float = 1.0,
    signal_weight: float = 1.0,
    tick_size: float = 1.0,
    max_abs_signal: float | None = None,
) -> SignalReference:
    scale = abs(float(signal_scale))
    if scale <= 0.0:
        scale = 1.0

    centered_signal = (float(signal_value) - float(baseline)) / scale
    clipped_signal = centered_signal
    if max_abs_signal is not None:
        max_abs_signal = abs(float(max_abs_signal))
        if max_abs_signal > 0.0:
            clipped_signal = max(-max_abs_signal, min(max_abs_signal, clipped_signal))

    fair_shift = clipped_signal * float(signal_weight) * float(tick_size)
    fair_value = float(base_fair) + fair_shift
    return SignalReference(
        raw_value=float(signal_value),
        centered_signal=centered_signal,
        clipped_signal=clipped_signal,
        fair_shift=fair_shift,
        fair_value=fair_value,
    )
