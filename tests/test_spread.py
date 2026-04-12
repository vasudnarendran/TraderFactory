from trader_factory.strategies.spread import linked_reference_fair, normalize_relationships


def test_normalize_relationships_uses_defaults_when_details_missing() -> None:
    relationships = normalize_relationships(related_symbols=["B"], relationship_details=None, default_hedge_ratio=1.25)
    assert len(relationships) == 1
    assert relationships[0].counterpart == "B"
    assert relationships[0].hedge_ratio == 1.25


def test_linked_reference_fair_blends_own_and_related_prices() -> None:
    fair = linked_reference_fair(
        own_mid=100.0,
        related_mid_prices={"B": 98.0},
        related_symbols=["B"],
        relationship_details=[{"counterpart": "B", "hedge_ratio": 1.5}],
        reference_weight=0.75,
    )
    assert fair is not None
    assert round(fair, 2) == 135.25


def test_linked_reference_fair_returns_none_without_reference_prices() -> None:
    fair = linked_reference_fair(
        own_mid=100.0,
        related_mid_prices={"B": None},
        related_symbols=["B"],
        reference_weight=0.75,
    )
    assert fair is None
