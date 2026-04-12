from __future__ import annotations

from dataclasses import dataclass
from math import erf, exp, log, sqrt


@dataclass(frozen=True)
class OptionReference:
    fair_value: float
    delta: float
    intrinsic_value: float
    time_to_expiry_years: float


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))


def _intrinsic_value(spot: float, strike: float, option_kind: str) -> float:
    kind = str(option_kind).strip().lower()
    if kind == "put":
        return max(float(strike) - float(spot), 0.0)
    return max(float(spot) - float(strike), 0.0)


def black_scholes_option_reference(
    *,
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    volatility: float,
    option_kind: str,
    risk_free_rate: float = 0.0,
    carry_rate: float = 0.0,
) -> OptionReference:
    kind = str(option_kind).strip().lower()
    if kind not in {"call", "put"}:
        raise ValueError(f"Unsupported option kind: {option_kind!r}")

    spot = float(spot)
    strike = float(strike)
    time_to_expiry_years = max(0.0, float(time_to_expiry_years))
    volatility = max(0.0, float(volatility))
    risk_free_rate = float(risk_free_rate)
    carry_rate = float(carry_rate)

    intrinsic_value = _intrinsic_value(spot, strike, kind)
    if strike <= 0.0 or spot <= 0.0:
        return OptionReference(
            fair_value=intrinsic_value,
            delta=0.0,
            intrinsic_value=intrinsic_value,
            time_to_expiry_years=time_to_expiry_years,
        )

    if time_to_expiry_years <= 0.0 or volatility <= 0.0:
        if kind == "call":
            if spot > strike:
                delta = 1.0
            elif spot < strike:
                delta = 0.0
            else:
                delta = 0.5
        else:
            if spot < strike:
                delta = -1.0
            elif spot > strike:
                delta = 0.0
            else:
                delta = -0.5
        return OptionReference(
            fair_value=intrinsic_value,
            delta=delta,
            intrinsic_value=intrinsic_value,
            time_to_expiry_years=time_to_expiry_years,
        )

    sigma_sqrt_t = volatility * sqrt(time_to_expiry_years)
    d1 = (
        log(spot / strike)
        + (risk_free_rate - carry_rate + 0.5 * volatility * volatility) * time_to_expiry_years
    ) / sigma_sqrt_t
    d2 = d1 - sigma_sqrt_t

    discounted_spot = spot * exp(-carry_rate * time_to_expiry_years)
    discounted_strike = strike * exp(-risk_free_rate * time_to_expiry_years)

    if kind == "call":
        fair_value = discounted_spot * _normal_cdf(d1) - discounted_strike * _normal_cdf(d2)
        delta = exp(-carry_rate * time_to_expiry_years) * _normal_cdf(d1)
    else:
        fair_value = discounted_strike * _normal_cdf(-d2) - discounted_spot * _normal_cdf(-d1)
        delta = -exp(-carry_rate * time_to_expiry_years) * _normal_cdf(-d1)

    return OptionReference(
        fair_value=fair_value,
        delta=delta,
        intrinsic_value=intrinsic_value,
        time_to_expiry_years=time_to_expiry_years,
    )
