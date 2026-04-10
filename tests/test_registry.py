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
    names = [cap.name for cap in recommend_capabilities(product)]
    assert "static_anchor_mm" in names

