from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class SpecTemplateDefinition:
    name: str
    summary: str
    builder: Callable[[str, str], dict[str, Any]]


def _generic_round_template(competition_name: str, round_name: str) -> dict[str, Any]:
    return {
        "name": competition_name,
        "round_name": round_name,
        "description": "Generic intake template for a new round. Replace placeholder products and mechanics with the actual round brief.",
        "mechanics": [],
        "products": [
            {
                "symbol": "PRODUCT_A",
                "position_limit": 20,
                "tick_size": 1.0,
                "price_regime": "mixed",
                "execution_style": "mixed",
                "mechanics": ["market_making", "inventory_sensitive"],
                "observations": [],
                "observation_channels": [],
                "unknown_mechanics": [],
                "open_questions": [],
                "notes": "Replace this placeholder with the first real product from the round brief.",
            },
            {
                "symbol": "PRODUCT_B",
                "position_limit": 20,
                "tick_size": 1.0,
                "price_regime": "mixed",
                "execution_style": "mixed",
                "mechanics": ["market_making", "inventory_sensitive"],
                "observations": [],
                "observation_channels": [],
                "unknown_mechanics": [],
                "open_questions": [],
                "notes": "Replace this placeholder with the second real product from the round brief.",
            },
        ],
        "relationships": [],
        "special_rules": [],
        "constraints": [],
        "open_questions": [],
        "unknown_mechanics": [],
        "research_goals": [
            "Keep unresolved mechanics explicit instead of guessing them away.",
            "Run validate-spec before scaffolding or optimization.",
        ],
    }


def _derivative_round_template(competition_name: str, round_name: str) -> dict[str, Any]:
    return {
        "name": competition_name,
        "round_name": round_name,
        "description": "Starter template for a round with one underlying asset and one vanilla option-style product.",
        "mechanics": [
            {
                "name": "anchored",
                "description": "Underlying product stays near a stable or slowly varying fair value.",
                "tags": ["stable_fair", "market_making"],
            },
            {
                "name": "option",
                "description": "Derivative product has a nonlinear payoff against an underlying.",
                "tags": ["expiry"],
            },
        ],
        "products": [
            {
                "symbol": "UNDERLYING",
                "position_limit": 100,
                "tick_size": 1.0,
                "price_regime": "anchored",
                "execution_style": "mixed",
                "mechanics": ["anchored", "market_making", "inventory_sensitive"],
                "notes": "Replace the placeholder name and confirm whether the fair is stable, drifting, or signal-driven.",
            },
            {
                "symbol": "CALL_100",
                "position_limit": 20,
                "tick_size": 1.0,
                "price_regime": "derivative",
                "execution_style": "mixed",
                "mechanics": ["option", "expiry"],
                "derivative_contract": {
                    "underlying": "UNDERLYING",
                    "option_kind": "call",
                    "strike": 100.0,
                    "time_to_expiry_years": 0.25,
                    "volatility": 0.25,
                    "risk_free_rate": 0.0,
                    "carry_rate": 0.0,
                    "expiry_style": "european",
                },
                "notes": "Confirm strike grid, expiry clock, volatility convention, and settlement rule before promotion.",
            },
        ],
        "relationships": [],
        "special_rules": [],
        "constraints": [
            "Option valuation should use the round's actual settlement convention, not a guessed payoff.",
        ],
        "open_questions": [],
        "unknown_mechanics": [],
        "research_goals": [
            "Confirm that the derivative is a vanilla payoff before trusting generated pricing logic.",
            "Validate whether local replay supports the same expiry and settlement assumptions as the official simulator.",
        ],
    }


def _linked_round_template(competition_name: str, round_name: str) -> dict[str, Any]:
    return {
        "name": competition_name,
        "round_name": round_name,
        "description": "Starter template for a round with linked or basket-style products.",
        "mechanics": [
            {
                "name": "pair_linked",
                "description": "Product fair depends on one or more related products.",
                "tags": ["spread_relationship", "basket"],
            }
        ],
        "products": [
            {
                "symbol": "LEG_A",
                "position_limit": 50,
                "tick_size": 1.0,
                "price_regime": "mixed",
                "execution_style": "mixed",
                "mechanics": ["market_making", "inventory_sensitive"],
                "notes": "Replace with the first linked component.",
            },
            {
                "symbol": "LEG_B",
                "position_limit": 50,
                "tick_size": 1.0,
                "price_regime": "mixed",
                "execution_style": "mixed",
                "mechanics": ["market_making", "inventory_sensitive"],
                "notes": "Replace with the second linked component.",
            },
            {
                "symbol": "BASKET_X",
                "position_limit": 30,
                "tick_size": 1.0,
                "price_regime": "linked",
                "execution_style": "mixed",
                "mechanics": ["basket", "pair_linked"],
                "basket_definition": {
                    "components": [
                        {"symbol": "LEG_A", "weight": 2.0},
                        {"symbol": "LEG_B", "weight": -1.0},
                    ],
                    "divisor": 1.0,
                    "fair_offset": 0.0,
                },
                "notes": "Confirm weights, offsets, and whether own-mid fallback is ever acceptable.",
            },
        ],
        "relationships": [
            {
                "left": "LEG_A",
                "right": "LEG_B",
                "relationship": "spread",
                "hedge_ratio": 1.0,
                "description": "Optional pair relationship if the round brief explicitly supports it.",
            }
        ],
        "special_rules": [],
        "constraints": [],
        "open_questions": [],
        "unknown_mechanics": [],
        "research_goals": [
            "Confirm that linked-product fair calculations should rely on traded mids and not hidden settlement values.",
            "Separate structural linkage questions from execution-transfer questions.",
        ],
    }


def _signal_participant_round_template(competition_name: str, round_name: str) -> dict[str, Any]:
    return {
        "name": competition_name,
        "round_name": round_name,
        "description": "Starter template for rounds with external observation feeds or named-participant mechanics.",
        "mechanics": [
            {
                "name": "external_signal",
                "description": "Product fair is modified by an external or plain observation feed.",
                "tags": ["signal"],
            },
            {
                "name": "named_participant",
                "description": "Specific participants carry information worth following or fading.",
                "tags": ["flow_following", "informed_trader"],
            },
        ],
        "products": [
            {
                "symbol": "WEATHER_GOOD",
                "position_limit": 40,
                "tick_size": 1.0,
                "price_regime": "mixed",
                "execution_style": "mixed",
                "mechanics": ["external_signal"],
                "observation_channels": [
                    {
                        "key": "WEATHER_SIGNAL",
                        "kind": "plain",
                        "role": "signal",
                        "description": "Plain observation feed that should influence fair value.",
                    }
                ],
                "signal_rule": {
                    "source_key": "WEATHER_SIGNAL",
                    "latency_hint": "one_step",
                    "staleness_limit": 3,
                    "interpretation_mode": "fair_shift",
                },
                "notes": "Confirm signal units, baseline, and whether staleness should disable or merely downweight the sleeve.",
            },
            {
                "symbol": "FLOW_GOOD",
                "position_limit": 40,
                "tick_size": 1.0,
                "price_regime": "mixed",
                "execution_style": "mixed",
                "mechanics": ["named_participant", "flow_following"],
                "participant_rule": {
                    "tracked_participants": ["Olivia", "Mia"],
                    "follow_mode": "fade",
                    "participant_weights": {"Olivia": 2.0, "Mia": 1.0},
                    "signal_horizon": 5,
                },
                "notes": "Replace placeholder participant IDs with the real round semantics before promotion.",
            },
        ],
        "relationships": [],
        "special_rules": [],
        "constraints": [],
        "open_questions": [],
        "unknown_mechanics": [],
        "research_goals": [
            "Confirm whether the external signal is contemporaneous, lagged, or partially stale in replay.",
            "Verify how participant identity appears in the official feed before relying on participant-flow logic.",
        ],
    }


def _conversion_auction_round_template(competition_name: str, round_name: str) -> dict[str, Any]:
    return {
        "name": competition_name,
        "round_name": round_name,
        "description": "Starter template for rounds with conversion economics or auction windows.",
        "mechanics": [
            {
                "name": "conversion",
                "description": "Product can be transformed or compared against an alternate venue or state with explicit economics.",
                "tags": ["transport"],
            },
            {
                "name": "auction",
                "description": "Trading edge depends on scheduled auction clears rather than continuous quoting alone.",
                "tags": [],
            },
        ],
        "products": [
            {
                "symbol": "LOCAL_GOOD",
                "position_limit": 50,
                "tick_size": 1.0,
                "price_regime": "mixed",
                "execution_style": "mixed",
                "mechanics": ["conversion", "transport"],
                "conversion_rule": {
                    "ratio": 1.0,
                    "fee": 1.5,
                    "delay_steps": 2,
                    "lot_size": 5,
                    "target_product": "REMOTE_GOOD",
                },
                "notes": "Confirm whether conversion actions are allowed, not just conversion observations.",
            },
            {
                "symbol": "REMOTE_GOOD",
                "position_limit": 50,
                "tick_size": 1.0,
                "price_regime": "mixed",
                "execution_style": "mixed",
                "mechanics": ["market_making"],
                "notes": "Placeholder remote or transformed reference product. Replace if the round uses a nontradable conversion reference instead.",
            },
            {
                "symbol": "AUCTION_GOOD",
                "position_limit": 40,
                "tick_size": 1.0,
                "price_regime": "auction",
                "execution_style": "mixed",
                "mechanics": ["auction"],
                "auction_rule": {
                    "schedule": "open_and_close",
                    "clearing_rule": "uniform_price",
                    "prep_window": 10,
                    "submission_window": 5,
                    "visibility": ["imbalance", "indicative_price"],
                },
                "notes": "Confirm visibility, cutoffs, and whether pre-auction inventory can be carried intentionally.",
            },
        ],
        "relationships": [],
        "special_rules": [],
        "constraints": [
            "Confirm whether conversion actions settle immediately, with delay, or only through explicit commands.",
        ],
        "open_questions": [],
        "unknown_mechanics": [],
        "research_goals": [
            "Separate conversion-pricing logic from conversion-action semantics.",
            "Confirm whether auction windows require a dedicated execution sleeve instead of default quoting.",
        ],
    }


SPEC_TEMPLATES: dict[str, SpecTemplateDefinition] = {
    "generic": SpecTemplateDefinition(
        name="generic",
        summary="Neutral starter round with two placeholder products and no structural mechanics.",
        builder=_generic_round_template,
    ),
    "derivative": SpecTemplateDefinition(
        name="derivative",
        summary="Underlying plus vanilla option-style product using `derivative_contract`.",
        builder=_derivative_round_template,
    ),
    "linked": SpecTemplateDefinition(
        name="linked",
        summary="Linked-products template using `relationships` and `basket_definition`.",
        builder=_linked_round_template,
    ),
    "signal_participant": SpecTemplateDefinition(
        name="signal_participant",
        summary="Signal-driven and participant-driven products using `observation_channels`, `signal_rule`, and `participant_rule`.",
        builder=_signal_participant_round_template,
    ),
    "conversion_auction": SpecTemplateDefinition(
        name="conversion_auction",
        summary="Conversion and auction mechanics using `conversion_rule` and `auction_rule`.",
        builder=_conversion_auction_round_template,
    ),
}


def available_spec_templates() -> list[SpecTemplateDefinition]:
    return [SPEC_TEMPLATES[name] for name in sorted(SPEC_TEMPLATES)]


def render_spec_template(
    template_name: str,
    *,
    competition_name: str = "NewCompetition",
    round_name: str = "round_1",
) -> dict[str, Any]:
    try:
        template = SPEC_TEMPLATES[template_name]
    except KeyError as exc:
        raise ValueError(f"Unknown spec template: {template_name}") from exc
    return template.builder(competition_name, round_name)
