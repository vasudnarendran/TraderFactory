from trader_factory.core.specs import ProductSpec
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
