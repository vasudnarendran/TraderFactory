from trader_factory.core.specs import CompetitionSpec


def test_competition_spec_parses_extended_intake_fields() -> None:
    spec = CompetitionSpec.from_dict(
        {
            "name": "TestComp",
            "round_name": "round_x",
            "open_questions": ["Need to confirm conversion semantics."],
            "unknown_mechanics": ["Settlement rule is partially unknown."],
            "special_rules": [
                {
                    "name": "conversion_rule",
                    "scope": "round",
                    "description": "Products can be converted under specific conditions.",
                    "open_questions": ["What is the conversion latency?"],
                }
            ],
            "relationships": [
                {
                    "left": "A",
                    "right": "B",
                    "relationship": "spread",
                    "hedge_ratio": 2.0,
                }
            ],
            "products": [
                {
                    "symbol": "A",
                    "position_limit": 10,
                    "mechanics": ["pair_linked"],
                    "unknown_mechanics": ["Settlement edge case."],
                    "special_rules": ["Conversion only works in fixed lots."],
                    "open_questions": ["What is the lot size?"],
                    "observation_channels": [
                        {
                            "key": "WEATHER_SIGNAL",
                            "kind": "plain",
                            "role": "signal",
                            "description": "External weather feed.",
                        }
                    ],
                    "custom_fields": {"underlying": "B"},
                }
            ],
        }
    )

    assert spec.open_questions == ["Need to confirm conversion semantics."]
    assert spec.unknown_mechanics == ["Settlement rule is partially unknown."]
    assert spec.special_rules[0].name == "conversion_rule"
    assert spec.special_rules[0].open_questions == ["What is the conversion latency?"]
    assert spec.relationships[0].counterpart("A") == "B"
    product = spec.products[0]
    assert product.unknown_mechanics == ["Settlement edge case."]
    assert product.special_rules == ["Conversion only works in fixed lots."]
    assert product.observation_channels[0].key == "WEATHER_SIGNAL"
    assert product.observation_channels[0].kind == "plain"
    assert product.observation_channels[0].role == "signal"
    assert product.custom_fields == {"underlying": "B"}


def test_product_spec_accepts_structured_observation_channels_inside_legacy_observations_field() -> None:
    spec = CompetitionSpec.from_dict(
        {
            "name": "TestComp",
            "round_name": "round_obs",
            "products": [
                {
                    "symbol": "SIG",
                    "position_limit": 10,
                    "observations": [
                        {"key": "SUNLIGHT", "kind": "plain", "role": "signal"},
                        "qualitative note",
                    ],
                }
            ],
        }
    )

    product = spec.products[0]
    assert product.observations == ["qualitative note"]
    assert product.observation_channels[0].key == "SUNLIGHT"
    assert product.observation_channels[0].role == "signal"


def test_product_spec_parses_typed_derivative_conversion_and_auction_schemas() -> None:
    spec = CompetitionSpec.from_dict(
        {
            "name": "TestComp",
            "round_name": "round_structured",
            "products": [
                {
                    "symbol": "CALL_100",
                    "position_limit": 10,
                    "mechanics": ["option", "conversion", "auction"],
                    "derivative_contract": {
                        "underlying": "SPOT",
                        "strike": 100.0,
                        "option_kind": "call",
                        "time_to_expiry_years": 0.25,
                        "volatility": 0.2,
                    },
                    "conversion_rule": {
                        "ratio": 2.0,
                        "fee": 1.5,
                        "delay_steps": 3,
                        "lot_size": 5,
                        "target_product": "SPOT",
                    },
                    "auction_rule": {
                        "schedule": "open_and_close",
                        "clearing_rule": "uniform_price",
                        "prep_window": 10,
                        "visibility": ["imbalance", "indicative_price"],
                    },
                }
            ],
        }
    )

    product = spec.products[0]
    assert product.derivative_contract is not None
    assert product.derivative_contract.underlying == "SPOT"
    assert product.derivative_contract.option_kind == "call"
    assert product.conversion_rule is not None
    assert product.conversion_rule.ratio == 2.0
    assert product.conversion_rule.fee == 1.5
    assert product.auction_rule is not None
    assert product.auction_rule.clearing_rule == "uniform_price"
    assert product.auction_rule.visibility == ["imbalance", "indicative_price"]


def test_product_spec_backfills_typed_schemas_from_legacy_custom_fields() -> None:
    spec = CompetitionSpec.from_dict(
        {
            "name": "TestComp",
            "round_name": "round_legacy",
            "products": [
                {
                    "symbol": "LEGACY",
                    "position_limit": 10,
                    "custom_fields": {
                        "underlying": "SPOT",
                        "strike": 100.0,
                        "option_kind": "put",
                        "time_to_expiry_years": 0.5,
                        "volatility": 0.3,
                        "conversion_ratio": 2.0,
                        "conversion_fee": 1.0,
                        "transport_delay": 2,
                        "lot_size": 4,
                        "auction_schedule": "close_only",
                        "clearing_rule": "uniform_price",
                        "pre_open_window": 8,
                    },
                }
            ],
        }
    )

    product = spec.products[0]
    assert product.derivative_contract is not None
    assert product.derivative_contract.option_kind == "put"
    assert product.conversion_rule is not None
    assert product.conversion_rule.ratio == 2.0
    assert product.conversion_rule.delay_steps == 2
    assert product.auction_rule is not None
    assert product.auction_rule.schedule == "close_only"


def test_product_spec_parses_typed_basket_participant_and_signal_schemas() -> None:
    spec = CompetitionSpec.from_dict(
        {
            "name": "TestComp",
            "round_name": "round_more_structured",
            "products": [
                {
                    "symbol": "STRUCTURED",
                    "position_limit": 10,
                    "basket_definition": {
                        "components": [
                            {"symbol": "A", "weight": 2.0},
                            {"symbol": "B", "weight": -1.0, "offset": 3.0},
                        ],
                        "divisor": 1.0,
                        "fair_offset": 2.0,
                    },
                    "participant_rule": {
                        "tracked_participants": ["Olivia", "Mia"],
                        "follow_mode": "fade",
                        "participant_weights": {"Olivia": 2.0},
                        "signal_horizon": 5,
                    },
                    "signal_rule": {
                        "source_key": "WEATHER_SIGNAL",
                        "latency_hint": "one_step",
                        "staleness_limit": 3,
                    },
                }
            ],
        }
    )

    product = spec.products[0]
    assert product.basket_definition is not None
    assert [component.symbol for component in product.basket_definition.components] == ["A", "B"]
    assert product.basket_definition.fair_offset == 2.0
    assert product.participant_rule is not None
    assert product.participant_rule.follow_mode == "fade"
    assert product.participant_rule.participant_weights == {"Olivia": 2.0}
    assert product.signal_rule is not None
    assert product.signal_rule.source_key == "WEATHER_SIGNAL"
    assert product.signal_rule.staleness_limit == 3


def test_product_spec_backfills_basket_participant_and_signal_schemas_from_legacy_custom_fields() -> None:
    spec = CompetitionSpec.from_dict(
        {
            "name": "TestComp",
            "round_name": "round_legacy_more",
            "products": [
                {
                    "symbol": "LEGACY_MORE",
                    "position_limit": 10,
                    "custom_fields": {
                        "components": [
                            {"symbol": "A", "weight": 2.0},
                            {"symbol": "B", "weight": -1.0},
                        ],
                        "basket_divisor": 1.0,
                        "fair_offset": 3.0,
                        "tracked_participants": ["Olivia", "Mia"],
                        "follow_mode": "fade",
                        "participant_weights": {"Olivia": 2.0},
                        "signal_source": "WEATHER_SIGNAL",
                        "signal_latency": "one_step",
                    },
                }
            ],
        }
    )

    product = spec.products[0]
    assert product.basket_definition is not None
    assert len(product.basket_definition.components) == 2
    assert product.basket_definition.divisor == 1.0
    assert product.participant_rule is not None
    assert product.participant_rule.tracked_participants == ["Olivia", "Mia"]
    assert product.participant_rule.follow_mode == "fade"
    assert product.signal_rule is not None
    assert product.signal_rule.source_key == "WEATHER_SIGNAL"
    assert product.signal_rule.latency_hint == "one_step"
