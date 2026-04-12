import json
from pathlib import Path

from trader_factory.core.specs import CompetitionSpec
from trader_factory.core.validation import validate_competition_spec
from trader_factory.intake import (
    create_intake_workspace,
    extract_spec_from_brief,
    extract_spec_with_report,
    render_extraction_markdown,
    render_round_brief_template,
)


def test_render_round_brief_template_produces_structured_products() -> None:
    brief = render_round_brief_template(
        "derivative",
        competition_name="DemoComp",
        round_name="round_demo",
    )

    assert brief["competition_name"] == "DemoComp"
    assert brief["round_name"] == "round_demo"
    assert brief["profile"] == "derivative"
    assert brief["products"][1]["mechanic_hypotheses"] == ["option", "expiry"]
    assert "derivative_contract" in brief["products"][1]


def test_extract_spec_from_brief_round_trips_into_valid_competition_spec() -> None:
    brief = render_round_brief_template(
        "signal_participant",
        competition_name="DemoComp",
        round_name="round_demo",
    )
    brief["products"][0]["raw_brief_excerpt"] = "Signal comes from the weather satellite."
    brief["products"][1]["source_notes"] = ["Participant names may be anonymized in official logs."]

    spec_payload = extract_spec_from_brief(brief)
    spec = CompetitionSpec.from_dict(spec_payload)
    report = validate_competition_spec(spec)

    assert spec.name == "DemoComp"
    assert spec.round_name == "round_demo"
    assert spec.products[0].signal_rule is not None
    assert spec.products[1].participant_rule is not None
    assert report.counts_by_severity()["error"] == 0


def test_extract_spec_from_brief_uses_hint_fields_and_writes_extraction_notes() -> None:
    brief = render_round_brief_template(
        "generic",
        competition_name="DemoComp",
        round_name="round_hints",
    )
    brief["products"][0]["symbol"] = "COCONUT"
    brief["products"][1]["symbol"] = "COCONUT_CALL_100"
    brief["products"][1]["mechanic_hypotheses"] = []
    brief["products"][1]["underlying_hint"] = "COCONUT"
    brief["products"][1]["raw_brief_excerpt"] = "This option expires in one quarter and references COCONUT."
    brief["products"][1]["related_products_hint"] = ["COCONUT"]
    brief["products"][1]["relationship_style_hint"] = "linked"

    spec_payload, extraction_report = extract_spec_with_report(brief)
    spec = CompetitionSpec.from_dict(spec_payload)
    derivative = next(product for product in spec.products if product.symbol == "COCONUT_CALL_100")
    report_text = render_extraction_markdown(extraction_report)

    assert derivative.derivative_contract is not None
    assert derivative.derivative_contract.underlying == "COCONUT"
    assert "option" in derivative.mechanics
    assert "expiry" in derivative.mechanics
    assert any(relationship.right == "COCONUT" or relationship.left == "COCONUT" for relationship in spec.relationships)
    assert "Inferred mechanic label" in report_text
    assert "derivative_contract.underlying" in report_text


def test_extract_spec_from_brief_infers_signal_rule_and_observation_channel() -> None:
    brief = render_round_brief_template(
        "generic",
        competition_name="DemoComp",
        round_name="round_signal",
    )
    brief["products"] = [
        {
            "symbol": "WEATHER_FRUIT",
            "position_limit": 20,
            "tick_size": 1.0,
            "price_regime": "unknown",
            "execution_style": "unknown",
            "mechanic_hypotheses": [],
            "unknown_mechanics": [],
            "observations": [],
            "observation_channels": [],
            "derivative_contract": {},
            "conversion_rule": {},
            "auction_rule": {},
            "basket_definition": {},
            "participant_rule": {},
            "signal_rule": {},
            "special_rules": [],
            "open_questions": [],
            "notes": "Weather feed moves fair value and the trader mostly quotes passively.",
            "signal_source_hint": "WEATHER_SIGNAL",
            "raw_brief_excerpt": "The weather signal updates once per step.",
            "source_notes": [],
            "custom_fields": {},
        }
    ]

    spec_payload, extraction_report = extract_spec_with_report(brief)
    spec = CompetitionSpec.from_dict(spec_payload)
    product = spec.products[0]

    assert product.signal_rule is not None
    assert product.signal_rule.source_key == "WEATHER_SIGNAL"
    assert product.observation_channels[0].key == "WEATHER_SIGNAL"
    assert "external_signal" in product.mechanics
    assert product.execution_style == "mostly_passive"
    assert any(note.field == "observation_channels" for note in extraction_report.notes)


def test_create_intake_workspace_writes_expected_files(tmp_path: Path) -> None:
    result = create_intake_workspace(
        "linked",
        competition_name="DemoComp",
        round_name="round_linked",
        output_dir=tmp_path / "intake_workspace",
    )

    assert result.output_dir.exists()
    assert result.readme_path.exists()
    assert result.raw_brief_path.exists()
    assert result.round_brief_path.exists()
    assert result.spec_path.exists()
    assert result.extraction_report_path.exists()

    brief_payload = json.loads(result.round_brief_path.read_text())
    spec_payload = json.loads(result.spec_path.read_text())
    spec = CompetitionSpec.from_dict(spec_payload)
    report = validate_competition_spec(spec)

    assert brief_payload["profile"] == "linked"
    assert spec.products[-1].basket_definition is not None
    assert report.counts_by_severity()["error"] == 0
    assert "brief-to-spec" in result.readme_path.read_text()
    assert "Brief Extraction Report" in result.extraction_report_path.read_text()
