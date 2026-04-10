from __future__ import annotations

from dataclasses import dataclass, field

from trader_factory.core.specs import ProductSpec


@dataclass(slots=True)
class StrategyCapability:
    name: str
    summary: str
    applicable_mechanics: list[str] = field(default_factory=list)
    applicable_regimes: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


STRATEGY_REGISTRY: list[StrategyCapability] = [
    StrategyCapability(
        name="static_anchor_mm",
        summary="Anchored market making around a fixed or very slow fair value.",
        applicable_mechanics=["static_anchor", "anchored", "stable_fair"],
        applicable_regimes=["anchored", "stationary"],
        outputs=["fair_value", "quotes", "inventory_recycling"],
        risks=["gets run over if the product truly trends"],
    ),
    StrategyCapability(
        name="join_improve_mm",
        summary="Join or improve the touch when book structure is stable and spread capture matters.",
        applicable_mechanics=["book_stable", "maker_friendly", "spread_capture"],
        applicable_regimes=["anchored", "drifting", "range"],
        outputs=["quote_prices", "passive_participation"],
        risks=["pickoffs near the touch"],
    ),
    StrategyCapability(
        name="inventory_skew_mm",
        summary="Shift quote center or size to prevent inventory from running away.",
        applicable_mechanics=["inventory_sensitive", "market_making"],
        applicable_regimes=["anchored", "range", "drifting"],
        outputs=["reservation_shift", "passive_size_bias"],
        risks=["can reduce participation if overused"],
    ),
    StrategyCapability(
        name="short_horizon_regression_alpha",
        summary="Short-window forecast for products with local directional structure.",
        applicable_mechanics=["trend", "microstructure_alpha", "latent_fair"],
        applicable_regimes=["drifting", "trend", "mixed"],
        outputs=["predicted_edge", "fit_quality"],
        risks=["can overfit noisy microstructure"],
    ),
    StrategyCapability(
        name="residual_mean_reversion",
        summary="Mean reversion on detrended residuals rather than on raw price.",
        applicable_mechanics=["mean_reversion", "residual", "latent_fair"],
        applicable_regimes=["range", "mixed"],
        outputs=["reversion_signal", "veto_signal"],
        risks=["dangerous if applied directly in strong trends"],
    ),
    StrategyCapability(
        name="breakout_confirmation",
        summary="Only follow breaks when flow, persistence, and price movement agree.",
        applicable_mechanics=["breakout", "burst", "flow_sensitive"],
        applicable_regimes=["trend", "mixed", "volatile"],
        outputs=["breakout_score", "aggression_scaler"],
        risks=["can chase late if thresholds are weak"],
    ),
    StrategyCapability(
        name="pair_or_spread_trading",
        summary="Trade residuals between linked products, spreads, or baskets.",
        applicable_mechanics=["pair_linked", "basket", "spread_relationship"],
        applicable_regimes=["linked", "residual"],
        outputs=["spread_fair", "hedge_target"],
        risks=["bad hedge assumptions can amplify losses"],
    ),
    StrategyCapability(
        name="option_parity_and_hedging",
        summary="Derivative sleeve using theoretical value gaps and hedge-aware execution.",
        applicable_mechanics=["option", "derivative", "expiry"],
        applicable_regimes=["derivative"],
        outputs=["theoretical_value", "delta_bias", "hedge_orders"],
        risks=["wrong parity or hedge assumptions cause structural losses"],
    ),
    StrategyCapability(
        name="informed_flow_tracking",
        summary="React to persistent informed or privileged participants when they exist.",
        applicable_mechanics=["informed_trader", "named_participant", "flow_following"],
        applicable_regimes=["informed_flow"],
        outputs=["participant_bias", "follow_or_fade_signal"],
        risks=["signal decays quickly if late"],
    ),
    StrategyCapability(
        name="execution_probe_suite",
        summary="Research-mode probe family for dormant logic, passive fills, and aggressive markouts.",
        applicable_mechanics=["unknown_execution", "hidden_simulator", "transfer_gap"],
        applicable_regimes=["any"],
        outputs=["discoveries", "decision_boundary_reports"],
        risks=["research tool only; not direct alpha"],
    ),
]


def recommend_capabilities(product: ProductSpec) -> list[StrategyCapability]:
    mechanics = set(product.mechanics)
    regime = product.price_regime
    matches: list[tuple[int, StrategyCapability]] = []
    for capability in STRATEGY_REGISTRY:
        score = 0
        score += sum(1 for item in capability.applicable_mechanics if item in mechanics)
        if regime in capability.applicable_regimes or "any" in capability.applicable_regimes:
            score += 1
        if score > 0:
            matches.append((score, capability))
    matches.sort(key=lambda item: (-item[0], item[1].name))
    return [capability for _, capability in matches]

