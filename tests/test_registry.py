from trader_factory.core.specs import CompetitionSpec, ProductSpec
from trader_factory.core.mapping import interpret_product
from trader_factory.core.registry import recommend_capabilities


def test_registry_returns_anchor_mm_for_anchored_product() -> None:
    product = ProductSpec(
        symbol="TEST",
        position_limit=10,
        price_regime="anchored",
        execution_style="mostly_passive",
        mechanics=["anchored", "static_anchor", "market_making"],
    )
    capabilities = recommend_capabilities(product)
    names = [cap.name for cap in capabilities]
    assert "static_anchor_mm" in names
    anchor = next(cap for cap in capabilities if cap.name == "static_anchor_mm")
    assert "market_making_and_quoting" in anchor.families
    assert "fair_value_and_mean_reversion" in anchor.families
    assert anchor.readiness == "factory_ready"


def test_registry_does_not_return_probe_suite_without_matching_mechanics() -> None:
    product = ProductSpec(
        symbol="TEST",
        position_limit=10,
        price_regime="anchored",
        execution_style="mostly_passive",
        mechanics=["anchored", "static_anchor", "market_making"],
    )
    names = [cap.name for cap in recommend_capabilities(product)]
    assert "execution_probe_suite" not in names


def test_registry_marks_probe_suite_as_research_only() -> None:
    product = ProductSpec(
        symbol="TEST",
        position_limit=10,
        price_regime="mixed",
        execution_style="hybrid",
        mechanics=["unknown_execution", "hidden_simulator", "transfer_gap"],
    )
    capabilities = recommend_capabilities(product)
    probe = next(cap for cap in capabilities if cap.name == "execution_probe_suite")
    assert probe.families == ["execution_and_participation"]
    assert probe.readiness == "research_only"


def test_interpret_product_marks_execution_unknowns_as_research_overlay() -> None:
    product = ProductSpec(
        symbol="TEST",
        position_limit=10,
        price_regime="mixed",
        execution_style="mixed",
        mechanics=["microstructure_alpha", "trend", "unknown_execution"],
        unknown_mechanics=["Passive queue behavior is not fully understood."],
    )
    interpretation = interpret_product(product)
    assert interpretation.preferred_archetype == "directional_mm"
    assert interpretation.fallback_mode == "research_overlay"
    assert "boundary" in interpretation.research_triggers
    assert "passive_ladder" in interpretation.research_triggers


def test_interpret_product_uses_manual_review_for_structural_unknowns() -> None:
    product = ProductSpec(
        symbol="TEST",
        position_limit=10,
        price_regime="unknown",
        execution_style="unknown",
        mechanics=[],
        unknown_mechanics=["Nonlinear settlement payoff depends on an external signal."],
    )
    interpretation = interpret_product(product)
    assert interpretation.preferred_archetype == "uncertain_stub"
    assert interpretation.fallback_mode == "manual_review_required"
    assert interpretation.manual_design_required is True


def test_interpret_product_routes_simple_conversion_products_to_conversion_mm() -> None:
    product = ProductSpec(
        symbol="TEST",
        position_limit=10,
        price_regime="unknown",
        execution_style="mixed",
        mechanics=["conversion", "transport"],
    )
    interpretation = interpret_product(product)
    assert interpretation.preferred_archetype == "conversion_mm"
    assert interpretation.fallback_mode == "normal"
    assert interpretation.manual_design_required is False
    assert any("conversion observation pricing" in gap.lower() for gap in interpretation.intake_gaps)


def test_interpret_product_routes_explicit_vanilla_option_to_derivative_mm() -> None:
    product = ProductSpec.from_dict(
        {
            "symbol": "TEST",
            "position_limit": 10,
            "price_regime": "derivative",
            "execution_style": "mixed",
            "mechanics": ["option", "expiry"],
            "derivative_contract": {
                "underlying": "SPOT",
                "strike": 100.0,
                "option_kind": "call",
                "time_to_expiry_years": 0.25,
                "volatility": 0.2,
            },
        }
    )
    interpretation = interpret_product(product)
    assert interpretation.preferred_archetype == "derivative_mm"
    assert interpretation.fallback_mode == "normal"
    assert interpretation.manual_design_required is False
    assert any("volatility convention" in gap.lower() for gap in interpretation.intake_gaps)


def test_interpret_product_keeps_underdefined_option_in_derivative_stub() -> None:
    product = ProductSpec.from_dict(
        {
            "symbol": "TEST",
            "position_limit": 10,
            "price_regime": "derivative",
            "execution_style": "mixed",
            "mechanics": ["option", "expiry"],
            "derivative_contract": {"underlying": "SPOT", "strike": 100.0},
        }
    )
    interpretation = interpret_product(product)
    assert interpretation.preferred_archetype == "derivative_stub"
    assert interpretation.fallback_mode == "manual_design_required"


def test_interpret_product_keeps_convertible_products_in_conversion_stub() -> None:
    product = ProductSpec(
        symbol="TEST",
        position_limit=10,
        price_regime="unknown",
        execution_style="mixed",
        mechanics=["convertible", "conversion"],
    )
    interpretation = interpret_product(product)
    assert interpretation.preferred_archetype == "conversion_stub"
    assert interpretation.fallback_mode == "manual_design_required"


def test_interpret_product_routes_explicit_participant_products_to_participant_mm() -> None:
    product = ProductSpec.from_dict(
        {
            "symbol": "TEST",
            "position_limit": 10,
            "price_regime": "mixed",
            "execution_style": "mixed",
            "mechanics": ["named_participant", "flow_following"],
            "participant_rule": {
                "tracked_participants": ["Olivia", "Mia"],
                "follow_mode": "fade",
            },
        }
    )
    interpretation = interpret_product(product)
    assert interpretation.preferred_archetype == "participant_mm"
    assert interpretation.fallback_mode == "normal"
    assert interpretation.manual_design_required is False
    assert any("tracked participant ids" in gap.lower() for gap in interpretation.intake_gaps)


def test_interpret_product_routes_explicit_basket_products_to_basket_mm() -> None:
    product = ProductSpec.from_dict(
        {
            "symbol": "TEST",
            "position_limit": 10,
            "price_regime": "linked",
            "execution_style": "mixed",
            "mechanics": ["basket", "pair_linked"],
            "basket_definition": {
                "components": [
                    {"symbol": "A", "weight": 2.0},
                    {"symbol": "B", "weight": -1.0},
                ]
            },
        }
    )
    interpretation = interpret_product(product)
    assert interpretation.preferred_archetype == "basket_mm"
    assert interpretation.fallback_mode == "normal"
    assert interpretation.manual_design_required is False
    assert any("basket components" in gap.lower() for gap in interpretation.intake_gaps)


def test_interpret_product_keeps_implicit_participant_products_in_participant_stub() -> None:
    product = ProductSpec(
        symbol="TEST",
        position_limit=10,
        price_regime="mixed",
        execution_style="mixed",
        mechanics=["named_participant", "flow_following"],
    )
    interpretation = interpret_product(product)
    assert interpretation.preferred_archetype == "participant_stub"
    assert interpretation.fallback_mode == "manual_design_required"


def test_interpret_product_routes_external_signal_products_to_signal_stub() -> None:
    product = ProductSpec(
        symbol="TEST",
        position_limit=10,
        price_regime="mixed",
        execution_style="mixed",
        mechanics=["external_signal"],
    )
    interpretation = interpret_product(product)
    assert interpretation.preferred_archetype == "signal_stub"
    assert interpretation.fallback_mode == "manual_design_required"
    assert any("external signal" in gap.lower() for gap in interpretation.intake_gaps)


def test_interpret_product_routes_explicit_external_signal_products_to_signal_mm() -> None:
    product = ProductSpec.from_dict(
        {
            "symbol": "TEST",
            "position_limit": 10,
            "price_regime": "mixed",
            "execution_style": "mixed",
            "mechanics": ["external_signal"],
            "signal_rule": {"source_key": "WEATHER_SIGNAL"},
        }
    )
    interpretation = interpret_product(product)
    assert interpretation.preferred_archetype == "signal_mm"
    assert interpretation.fallback_mode == "normal"
    assert interpretation.manual_design_required is False
    assert any("signal source key" in gap.lower() for gap in interpretation.intake_gaps)


def test_interpret_product_routes_single_plain_signal_channel_to_signal_mm() -> None:
    product = ProductSpec.from_dict(
        {
            "symbol": "TEST",
            "position_limit": 10,
            "price_regime": "mixed",
            "execution_style": "mixed",
            "mechanics": ["external_signal"],
            "observation_channels": [
                {"key": "WEATHER_SIGNAL", "kind": "plain", "role": "signal"}
            ],
        }
    )
    interpretation = interpret_product(product)
    assert interpretation.preferred_archetype == "signal_mm"
    assert interpretation.fallback_mode == "normal"


def test_interpret_product_routes_simple_linked_pair_to_spread_mm() -> None:
    spec = CompetitionSpec.from_dict(
        {
            "name": "TestComp",
            "round_name": "round_pair",
            "relationships": [
                {"left": "A", "right": "B", "relationship": "spread", "hedge_ratio": 1.5}
            ],
            "products": [
                {
                    "symbol": "A",
                    "position_limit": 10,
                    "price_regime": "linked",
                    "execution_style": "mixed",
                    "mechanics": ["pair_linked", "spread_relationship"],
                }
            ],
        }
    )
    interpretation = interpret_product(spec.products[0], spec)
    assert interpretation.preferred_archetype == "spread_mm"
    assert interpretation.fallback_mode == "normal"
    assert interpretation.manual_design_required is False
    assert "B" in interpretation.related_products


def test_interpret_product_keeps_basket_in_spread_stub() -> None:
    spec = CompetitionSpec.from_dict(
        {
            "name": "TestComp",
            "round_name": "round_basket",
            "relationships": [
                {"left": "A", "right": "B", "relationship": "basket_leg", "hedge_ratio": 1.0},
                {"left": "A", "right": "C", "relationship": "basket_leg", "hedge_ratio": 1.0},
            ],
            "products": [
                {
                    "symbol": "A",
                    "position_limit": 10,
                    "price_regime": "linked",
                    "execution_style": "mixed",
                    "mechanics": ["basket", "pair_linked"],
                }
            ],
        }
    )
    interpretation = interpret_product(spec.products[0], spec)
    assert interpretation.preferred_archetype == "spread_stub"
    assert interpretation.fallback_mode == "manual_design_required"
