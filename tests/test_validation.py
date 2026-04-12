from trader_factory.core.specs import CompetitionSpec
from trader_factory.core.validation import render_validation_markdown, validate_competition_spec


def test_validate_competition_spec_blocks_underdefined_derivative_products() -> None:
    spec = CompetitionSpec.from_dict(
        {
            "name": "TestComp",
            "round_name": "round_validate_derivative",
            "products": [
                {
                    "symbol": "SPOT",
                    "position_limit": 20,
                    "tick_size": 1.0,
                    "price_regime": "anchored",
                    "execution_style": "mixed",
                    "mechanics": ["anchored"],
                },
                {
                    "symbol": "CALL_100",
                    "position_limit": 20,
                    "tick_size": 1.0,
                    "price_regime": "derivative",
                    "execution_style": "mixed",
                    "mechanics": ["option", "expiry"],
                    "derivative_contract": {
                        "underlying": "SPOT",
                        "strike": 100.0,
                        "option_kind": "call",
                    },
                },
            ],
        }
    )

    report = validate_competition_spec(spec)
    derivative_report = next(product for product in report.product_reports if product.symbol == "CALL_100")
    codes = {finding.code for finding in derivative_report.findings}
    markdown = render_validation_markdown(report)

    assert derivative_report.status == "blocked"
    assert "product.derivative_missing_expiry" in codes
    assert "product.derivative_missing_volatility" in codes
    assert "Status: `blocked`" in markdown
    assert "missing time to expiry" in markdown


def test_validate_competition_spec_reports_legacy_custom_field_usage() -> None:
    spec = CompetitionSpec.from_dict(
        {
            "name": "TestComp",
            "round_name": "round_validate_legacy",
            "products": [
                {
                    "symbol": "LEGACY",
                    "position_limit": 10,
                    "tick_size": 1.0,
                    "price_regime": "mixed",
                    "execution_style": "mixed",
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
                    },
                }
            ],
        }
    )

    report = validate_competition_spec(spec)
    legacy_report = report.product_reports[0]
    legacy_findings = [finding for finding in legacy_report.findings if finding.code == "product.legacy_custom_fields"]
    legacy_schemas = {finding.evidence["schema"] for finding in legacy_findings}

    assert legacy_report.status == "needs_review"
    assert "derivative_contract" in legacy_schemas
    assert "conversion_rule" in legacy_schemas


def test_validate_competition_spec_flags_invalid_relationships_and_signal_source_keys() -> None:
    spec = CompetitionSpec.from_dict(
        {
            "name": "TestComp",
            "round_name": "round_validate_links",
            "relationships": [
                {"left": "ALPHA", "right": "MISSING", "relationship": "spread"},
            ],
            "products": [
                {
                    "symbol": "ALPHA",
                    "position_limit": 20,
                    "tick_size": 1.0,
                    "price_regime": "mixed",
                    "execution_style": "mixed",
                    "mechanics": ["external_signal"],
                    "signal_rule": {"source_key": "WEATHER_SIGNAL"},
                }
            ],
        }
    )

    report = validate_competition_spec(spec)
    round_codes = {finding.code for finding in report.round_findings}
    product_codes = {finding.code for finding in report.product_reports[0].findings}

    assert "round.relationship_unknown_right" in round_codes
    assert "product.signal_unknown_source_key" in product_codes
