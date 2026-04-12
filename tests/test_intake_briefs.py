import json
from pathlib import Path

from trader_factory.core.specs import CompetitionSpec
from trader_factory.core.validation import validate_competition_spec
from trader_factory.intake import create_intake_workspace, extract_spec_from_brief, render_round_brief_template


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

    brief_payload = json.loads(result.round_brief_path.read_text())
    spec_payload = json.loads(result.spec_path.read_text())
    spec = CompetitionSpec.from_dict(spec_payload)
    report = validate_competition_spec(spec)

    assert brief_payload["profile"] == "linked"
    assert spec.products[-1].basket_definition is not None
    assert report.counts_by_severity()["error"] == 0
    assert "brief-to-spec" in result.readme_path.read_text()
