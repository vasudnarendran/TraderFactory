from __future__ import annotations

from dataclasses import dataclass, field

from trader_factory.core.registry import StrategyCapability, recommend_capabilities
from trader_factory.core.specs import CompetitionSpec, ProductSpec


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        cleaned = str(item).strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        ordered.append(cleaned)
    return ordered


@dataclass(slots=True)
class MechanicMapping:
    name: str
    archetype_hints: list[str] = field(default_factory=list)
    capability_hints: list[str] = field(default_factory=list)
    research_triggers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    manual_design_required: bool = False


KNOWN_MECHANIC_MAPPINGS: dict[str, MechanicMapping] = {
    "anchored": MechanicMapping(
        name="anchored",
        archetype_hints=["anchored_mm"],
        capability_hints=["static_anchor_mm", "join_improve_mm"],
    ),
    "static_anchor": MechanicMapping(
        name="static_anchor",
        archetype_hints=["anchored_mm"],
        capability_hints=["static_anchor_mm"],
    ),
    "stable_fair": MechanicMapping(
        name="stable_fair",
        archetype_hints=["anchored_mm"],
        capability_hints=["static_anchor_mm"],
    ),
    "book_stable": MechanicMapping(
        name="book_stable",
        archetype_hints=["simple_mm"],
        capability_hints=["join_improve_mm"],
    ),
    "market_making": MechanicMapping(
        name="market_making",
        archetype_hints=["simple_mm"],
        capability_hints=["join_improve_mm", "inventory_skew_mm"],
    ),
    "inventory_sensitive": MechanicMapping(
        name="inventory_sensitive",
        archetype_hints=["simple_mm"],
        capability_hints=["inventory_skew_mm"],
    ),
    "maker_friendly": MechanicMapping(
        name="maker_friendly",
        archetype_hints=["simple_mm"],
        capability_hints=["join_improve_mm"],
    ),
    "spread_capture": MechanicMapping(
        name="spread_capture",
        archetype_hints=["simple_mm"],
        capability_hints=["join_improve_mm"],
    ),
    "trend": MechanicMapping(
        name="trend",
        archetype_hints=["directional_mm"],
        capability_hints=["short_horizon_regression_alpha", "breakout_confirmation"],
    ),
    "microstructure_alpha": MechanicMapping(
        name="microstructure_alpha",
        archetype_hints=["directional_mm"],
        capability_hints=["short_horizon_regression_alpha"],
    ),
    "latent_fair": MechanicMapping(
        name="latent_fair",
        archetype_hints=["directional_mm"],
        capability_hints=["short_horizon_regression_alpha", "residual_mean_reversion"],
    ),
    "mean_reversion": MechanicMapping(
        name="mean_reversion",
        archetype_hints=["directional_mm"],
        capability_hints=["residual_mean_reversion"],
    ),
    "residual": MechanicMapping(
        name="residual",
        archetype_hints=["directional_mm"],
        capability_hints=["residual_mean_reversion"],
    ),
    "breakout": MechanicMapping(
        name="breakout",
        archetype_hints=["directional_mm"],
        capability_hints=["breakout_confirmation"],
    ),
    "burst": MechanicMapping(
        name="burst",
        archetype_hints=["directional_mm"],
        capability_hints=["breakout_confirmation"],
    ),
    "flow_sensitive": MechanicMapping(
        name="flow_sensitive",
        archetype_hints=["directional_mm"],
        capability_hints=["breakout_confirmation"],
    ),
    "pair_linked": MechanicMapping(
        name="pair_linked",
        archetype_hints=["spread_mm", "spread_stub"],
        capability_hints=["pair_or_spread_trading"],
        warnings=["Linked products should declare hedge relationships explicitly so the spread sleeve does not assume a default ratio."],
    ),
    "basket": MechanicMapping(
        name="basket",
        archetype_hints=["spread_stub"],
        capability_hints=["pair_or_spread_trading"],
        warnings=["Basket products need explicit component weights and hedge rules."],
        manual_design_required=True,
    ),
    "spread_relationship": MechanicMapping(
        name="spread_relationship",
        archetype_hints=["spread_mm", "spread_stub"],
        capability_hints=["pair_or_spread_trading"],
        warnings=["Spread sleeves should carry explicit relationship metadata before deployment."],
    ),
    "option": MechanicMapping(
        name="option",
        archetype_hints=["derivative_stub"],
        capability_hints=["option_parity_and_hedging"],
        warnings=["Derivative products need pricing inputs and settlement rules, not just generic quoting."],
        manual_design_required=True,
    ),
    "convertible": MechanicMapping(
        name="convertible",
        archetype_hints=["conversion_stub", "derivative_stub"],
        warnings=["Convertible products need both pricing logic and explicit conversion economics."],
        manual_design_required=True,
    ),
    "derivative": MechanicMapping(
        name="derivative",
        archetype_hints=["derivative_stub"],
        capability_hints=["option_parity_and_hedging"],
        warnings=["Derivative sleeves require explicit theoretical value assumptions."],
        manual_design_required=True,
    ),
    "expiry": MechanicMapping(
        name="expiry",
        archetype_hints=["derivative_stub"],
        capability_hints=["option_parity_and_hedging"],
        warnings=["Expiry handling must be described explicitly in the round spec."],
        manual_design_required=True,
    ),
    "volatility_surface": MechanicMapping(
        name="volatility_surface",
        archetype_hints=["derivative_stub"],
        warnings=["Volatility-surface mechanics require an explicit volatility model or approximation."],
        manual_design_required=True,
    ),
    "informed_trader": MechanicMapping(
        name="informed_trader",
        archetype_hints=["participant_stub"],
        capability_hints=["informed_flow_tracking"],
        warnings=["Participant-driven products need identity and timing assumptions before automation is safe."],
        manual_design_required=True,
    ),
    "named_participant": MechanicMapping(
        name="named_participant",
        archetype_hints=["participant_stub"],
        capability_hints=["informed_flow_tracking"],
        warnings=["Participant-driven sleeves should be reviewed before they are traded live."],
        manual_design_required=True,
    ),
    "flow_following": MechanicMapping(
        name="flow_following",
        archetype_hints=["participant_stub"],
        capability_hints=["informed_flow_tracking"],
        warnings=["Flow-following logic depends on clear participant semantics."],
        manual_design_required=True,
    ),
    "unknown_execution": MechanicMapping(
        name="unknown_execution",
        research_triggers=["boundary", "aggressive_markout", "passive_ladder"],
        warnings=["Execution transfer is unclear; keep development and probe logic separate."],
    ),
    "hidden_simulator": MechanicMapping(
        name="hidden_simulator",
        research_triggers=["boundary", "aggressive_markout", "passive_ladder"],
        warnings=["Official simulator details are hidden; probe before assuming passive edge transfers."],
    ),
    "transfer_gap": MechanicMapping(
        name="transfer_gap",
        research_triggers=["boundary", "aggressive_markout"],
        warnings=["Local and official behavior may diverge for this product."],
    ),
    "conversion": MechanicMapping(
        name="conversion",
        archetype_hints=["conversion_mm", "conversion_stub"],
        warnings=["Simple conversion-observation products can use observation-derived pricing, but conversion-action semantics should still be confirmed explicitly."],
    ),
    "settlement_formula": MechanicMapping(
        name="settlement_formula",
        archetype_hints=["derivative_stub"],
        warnings=["Settlement formulas should be captured explicitly in the spec or custom_fields."],
        manual_design_required=True,
    ),
    "auction": MechanicMapping(
        name="auction",
        archetype_hints=["auction_stub"],
        warnings=["Auction mechanics need a dedicated execution sleeve, not default market making."],
        manual_design_required=True,
    ),
    "storage": MechanicMapping(
        name="storage",
        archetype_hints=["storage_stub"],
        warnings=["Storage-constrained products need inventory state beyond the current simple sleeves."],
        manual_design_required=True,
    ),
    "transport": MechanicMapping(
        name="transport",
        archetype_hints=["conversion_stub"],
        warnings=["Transport mechanics need explicit latency or routing rules in the spec."],
        manual_design_required=True,
    ),
    "external_signal": MechanicMapping(
        name="external_signal",
        archetype_hints=["signal_mm", "signal_stub"],
        warnings=["External signals must be defined explicitly before the factory can automate them."],
        manual_design_required=True,
    ),
    "nonlinear_payoff": MechanicMapping(
        name="nonlinear_payoff",
        archetype_hints=["derivative_stub"],
        warnings=["Nonlinear payoffs require deliberate pricing logic and should not fall through to generic MM."],
        manual_design_required=True,
    ),
    "queue_sensitive": MechanicMapping(
        name="queue_sensitive",
        research_triggers=["boundary", "passive_ladder"],
        warnings=["Queue-sensitive products need explicit passive fill validation."],
    ),
    "thin_liquidity": MechanicMapping(
        name="thin_liquidity",
        research_triggers=["aggressive_markout", "passive_ladder"],
        warnings=["Thin liquidity can invalidate naive passive and aggressive sizing assumptions."],
    ),
    "impact_sensitive": MechanicMapping(
        name="impact_sensitive",
        research_triggers=["aggressive_markout"],
        warnings=["Impact-sensitive products need execution sizing discipline before optimization."],
    ),
    "uncertain_fair": MechanicMapping(
        name="uncertain_fair",
        warnings=["Fair value is unstable enough that quoting overlays should remain conservative until modeled explicitly."],
    ),
    "turbulent": MechanicMapping(
        name="turbulent",
        warnings=["Turbulent products likely need volatility-aware overlays rather than fixed quoting widths."],
    ),
    "portfolio_coupled": MechanicMapping(
        name="portfolio_coupled",
        warnings=["Portfolio-coupled products need cross-product risk coordination beyond single-product sleeves."],
        manual_design_required=True,
    ),
    "shared_risk_budget": MechanicMapping(
        name="shared_risk_budget",
        warnings=["Shared risk budgets should be encoded explicitly rather than inferred from position limits."],
        manual_design_required=True,
    ),
    "multi_signal": MechanicMapping(
        name="multi_signal",
        warnings=["Multi-signal products should define how signals blend before optimization begins."],
    ),
    "feature_overlap": MechanicMapping(
        name="feature_overlap",
        warnings=["Feature overlap should be handled deliberately to avoid double-counting the same edge."],
    ),
    "mixed_regime": MechanicMapping(
        name="mixed_regime",
        warnings=["Mixed-regime products may need explicit gating or state detection before one sleeve is trusted."],
    ),
}


@dataclass(slots=True)
class ProductInterpretation:
    symbol: str
    recognized_mechanics: list[str] = field(default_factory=list)
    unknown_mechanics: list[str] = field(default_factory=list)
    related_products: list[str] = field(default_factory=list)
    special_rules: list[str] = field(default_factory=list)
    recommended_capabilities: list[StrategyCapability] = field(default_factory=list)
    preferred_archetype: str = "simple_mm"
    fallback_mode: str = "normal"
    warnings: list[str] = field(default_factory=list)
    research_triggers: list[str] = field(default_factory=list)
    intake_gaps: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    manual_design_required: bool = False


def _applicable_rule_strings(spec: CompetitionSpec | None, product: ProductSpec) -> list[str]:
    if spec is None:
        return list(product.special_rules)
    rules = list(product.special_rules)
    for rule in spec.special_rules:
        if rule.scope == "round" or product.symbol in rule.applies_to:
            rules.append(rule.name or rule.description)
    return _unique(rules)


def _applicable_rule_questions(spec: CompetitionSpec | None, product: ProductSpec) -> list[str]:
    questions = list(product.open_questions)
    if spec is None:
        return _unique(questions)
    for rule in spec.special_rules:
        if rule.scope == "round" or product.symbol in rule.applies_to:
            questions.extend(rule.open_questions)
    return _unique(questions)


def _related_products(spec: CompetitionSpec | None, product: ProductSpec) -> list[str]:
    if spec is None:
        return []
    related: list[str] = []
    for relationship in spec.relationships_for(product.symbol):
        counterpart = relationship.counterpart(product.symbol)
        if counterpart:
            related.append(counterpart)
    return _unique(related)


def _is_structural_unknown(text: str) -> bool:
    lowered = text.lower()
    return any(
        keyword in lowered
        for keyword in (
            "option",
            "derivative",
            "payoff",
            "settlement",
            "conversion",
            "auction",
            "basket",
            "spread",
            "link",
            "expiry",
            "storage",
            "transport",
            "signal",
        )
    )


def _is_execution_unknown(text: str) -> bool:
    lowered = text.lower()
    return any(
        keyword in lowered
        for keyword in ("execution", "fill", "queue", "passive", "aggressive", "markout", "slippage", "simulator")
    )


def _normalize_custom_sequence(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = [value]
    return [str(item).strip() for item in raw_items if str(item).strip()]


def _has_explicit_vanilla_derivative_setup(product: ProductSpec) -> bool:
    contract = product.derivative_contract
    if contract is None:
        return False
    return bool(
        contract.underlying
        and contract.strike is not None
        and contract.option_kind in {"call", "put"}
        and contract.volatility is not None
        and contract.time_to_expiry_years is not None
    )


def _has_explicit_basket_setup(product: ProductSpec) -> bool:
    basket_definition = product.basket_definition
    if basket_definition is None or not basket_definition.components:
        return False
    valid_components = 0
    for component in basket_definition.components:
        if component.symbol:
            valid_components += 1
    return valid_components >= 2


def _has_explicit_signal_setup(product: ProductSpec) -> bool:
    signal_rule = product.signal_rule
    signal_source = "" if signal_rule is None else str(signal_rule.source_key).strip()
    if signal_source:
        return True
    signal_keys = product.observation_keys(kind="plain", role="signal")
    if len(signal_keys) == 1:
        return True
    observation_keys = product.observation_keys(kind="plain")
    if len(observation_keys) == 1:
        return True
    observation_keys = _normalize_custom_sequence(product.observations)
    return len(observation_keys) == 1


def _choose_preferred_archetype(
    product: ProductSpec,
    capability_names: set[str],
    *,
    related_products: list[str],
    structural_unknown: bool,
) -> str:
    mechanics = set(product.mechanics)
    participant_rule = product.participant_rule
    tracked_participants = [] if participant_rule is None else list(participant_rule.tracked_participants)
    if structural_unknown:
        return "uncertain_stub"
    if "convertible" in mechanics:
        return "conversion_stub"
    if "conversion" in mechanics:
        return "conversion_mm"
    if "transport" in mechanics:
        return "conversion_stub"
    if mechanics & {"auction"}:
        return "auction_stub"
    if mechanics & {"storage"}:
        return "storage_stub"
    if mechanics & {"external_signal"}:
        if _has_explicit_signal_setup(product):
            return "signal_mm"
        return "signal_stub"
    if "option_parity_and_hedging" in capability_names or mechanics & {"option", "derivative", "expiry", "settlement_formula", "nonlinear_payoff", "volatility_surface"}:
        if mechanics & {"settlement_formula", "nonlinear_payoff", "volatility_surface"}:
            return "derivative_stub"
        if _has_explicit_vanilla_derivative_setup(product):
            return "derivative_mm"
        return "derivative_stub"
    if "informed_flow_tracking" in capability_names or mechanics & {"informed_trader", "named_participant", "flow_following"}:
        if tracked_participants:
            return "participant_mm"
        return "participant_stub"
    if {"pair_or_spread_trading"} & capability_names or related_products or mechanics & {"pair_linked", "basket", "spread_relationship"}:
        if "basket" in mechanics:
            if _has_explicit_basket_setup(product):
                return "basket_mm"
            return "spread_stub"
        if len(related_products) == 1 and "basket" not in mechanics and product.basket_definition is None:
            return "spread_mm"
        return "spread_stub"
    if "static_anchor_mm" in capability_names:
        return "anchored_mm"
    if {"short_horizon_regression_alpha", "residual_mean_reversion", "breakout_confirmation"} & capability_names:
        return "directional_mm"
    if {"join_improve_mm", "inventory_skew_mm"} & capability_names:
        return "simple_mm"
    return "simple_mm"


def interpret_product(product: ProductSpec, spec: CompetitionSpec | None = None) -> ProductInterpretation:
    recognized_mechanics = [mechanic for mechanic in product.mechanics if mechanic in KNOWN_MECHANIC_MAPPINGS]
    unmapped_mechanics = [mechanic for mechanic in product.mechanics if mechanic not in KNOWN_MECHANIC_MAPPINGS]
    unknown_mechanics = _unique(unmapped_mechanics + product.unknown_mechanics)
    related_products = _related_products(spec, product)
    special_rules = _applicable_rule_strings(spec, product)
    open_questions = _applicable_rule_questions(spec, product)
    recommendations = recommend_capabilities(product)
    capability_names = {capability.name for capability in recommendations}

    warnings: list[str] = []
    research_triggers: list[str] = []
    manual_design_required = False

    for mechanic in recognized_mechanics:
        mapping = KNOWN_MECHANIC_MAPPINGS[mechanic]
        warnings.extend(mapping.warnings)
        research_triggers.extend(mapping.research_triggers)
        manual_design_required = manual_design_required or mapping.manual_design_required

    structural_unknown = any(_is_structural_unknown(item) for item in unknown_mechanics + special_rules)
    execution_unknown = any(_is_execution_unknown(item) for item in unknown_mechanics + special_rules)
    preferred_archetype = _choose_preferred_archetype(
        product,
        capability_names,
        related_products=related_products,
        structural_unknown=structural_unknown,
    )

    if structural_unknown:
        warnings.append("Structural mechanics remain unclassified; the generated trader will stay as a manual-review stub.")
    if execution_unknown:
        research_triggers.extend(["boundary", "aggressive_markout", "passive_ladder"])
        warnings.append("Execution assumptions are unresolved; use probes before trusting official transfer.")
    if product.execution_style == "unknown":
        warnings.append("Execution style is still unknown; confirm whether the product is maker, taker, or mixed.")

    intake_gaps: list[str] = []
    if preferred_archetype == "spread_stub" and not related_products:
        intake_gaps.append("Declare linked products or hedge ratios before relying on spread logic.")
    if preferred_archetype == "spread_mm":
        intake_gaps.append("Confirm hedge ratios explicitly if the default 1.0 assumption is not correct.")
    if preferred_archetype == "basket_mm":
        intake_gaps.append("Confirm basket components, weights, divisor, and premium offset before trusting the generated basket sleeve.")
    if preferred_archetype == "derivative_mm":
        intake_gaps.append("Confirm underlying symbol, strike, expiry clock, and volatility convention before trusting the generated option-pricing sleeve.")
    if preferred_archetype == "derivative_stub":
        intake_gaps.append("Capture derivative inputs such as underlying, strike, expiry, and settlement formula.")
    if preferred_archetype == "participant_stub":
        intake_gaps.append("Describe participant identity semantics and how they appear in the feed.")
    if preferred_archetype == "participant_mm":
        intake_gaps.append("Confirm tracked participant IDs and whether the sleeve should follow, fade, or only gate on their flow.")
    if preferred_archetype == "conversion_mm":
        intake_gaps.append("Confirm that conversion observation pricing is the correct local anchor before enabling conversion-specific actions.")
    if preferred_archetype == "conversion_stub":
        intake_gaps.append("Capture conversion ratios, fees, delays, lot sizes, and any target products explicitly.")
    if preferred_archetype == "auction_stub":
        intake_gaps.append("Capture the auction schedule, clearing rule, and what information is visible before clearing.")
    if preferred_archetype == "storage_stub":
        intake_gaps.append("Capture carry economics, storage limits, and how inventory persists across time.")
    if preferred_archetype == "signal_mm":
        intake_gaps.append("Confirm the signal source key, its scaling, and the maximum acceptable signal staleness before trusting the generated signal sleeve.")
    if preferred_archetype == "signal_stub":
        intake_gaps.append("Describe the external signal, its latency, and how it should modify fair value or sizing.")
    if structural_unknown:
        intake_gaps.append("Classify structural unknown mechanics before auto-generated logic is trusted.")
    if unknown_mechanics and not structural_unknown:
        intake_gaps.append("Map remaining unknown mechanics into the vocabulary or leave them as explicit agent-review notes.")
    if special_rules:
        intake_gaps.append("Translate special rules into machine-readable fields or custom_fields when they affect pricing or execution.")
    if open_questions:
        intake_gaps.append("Resolve open questions recorded in the spec before promotion.")

    if structural_unknown:
        fallback_mode = "manual_review_required"
    elif preferred_archetype in {
        "spread_stub",
        "derivative_stub",
        "participant_stub",
        "conversion_stub",
        "auction_stub",
        "storage_stub",
        "signal_stub",
    }:
        fallback_mode = "manual_design_required"
    elif research_triggers:
        fallback_mode = "research_overlay"
    else:
        fallback_mode = "normal"

    if preferred_archetype == "conversion_mm" and fallback_mode not in {"manual_design_required", "manual_review_required"}:
        manual_design_required = False
    if preferred_archetype == "participant_mm" and fallback_mode not in {"manual_design_required", "manual_review_required"}:
        manual_design_required = False
    if preferred_archetype == "basket_mm" and fallback_mode not in {"manual_design_required", "manual_review_required"}:
        manual_design_required = False
    if preferred_archetype == "derivative_mm" and fallback_mode not in {"manual_design_required", "manual_review_required"}:
        manual_design_required = False
    if preferred_archetype == "signal_mm" and fallback_mode not in {"manual_design_required", "manual_review_required"}:
        manual_design_required = False

    return ProductInterpretation(
        symbol=product.symbol,
        recognized_mechanics=recognized_mechanics,
        unknown_mechanics=unknown_mechanics,
        related_products=related_products,
        special_rules=special_rules,
        recommended_capabilities=recommendations,
        preferred_archetype=preferred_archetype,
        fallback_mode=fallback_mode,
        warnings=_unique(warnings),
        research_triggers=_unique(research_triggers),
        intake_gaps=_unique(intake_gaps),
        open_questions=open_questions,
        manual_design_required=manual_design_required or fallback_mode in {"manual_design_required", "manual_review_required"},
    )


def interpret_competition(spec: CompetitionSpec) -> dict[str, ProductInterpretation]:
    return {product.symbol: interpret_product(product, spec) for product in spec.products}
