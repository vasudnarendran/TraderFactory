import json
from pathlib import Path

from trader_factory.core.specs import CompetitionSpec
from trader_factory.core.validation import validate_competition_spec
from trader_factory.generation.spec_templates import SPEC_TEMPLATES, available_spec_templates, render_spec_template


def test_available_spec_templates_are_sorted_and_named() -> None:
    template_names = [template.name for template in available_spec_templates()]

    assert template_names == sorted(SPEC_TEMPLATES)
    assert template_names == [
        "conversion_auction",
        "derivative",
        "generic",
        "linked",
        "signal_participant",
    ]


def test_builtin_spec_templates_parse_and_validate_without_errors() -> None:
    for template_name in SPEC_TEMPLATES:
        payload = render_spec_template(
            template_name,
            competition_name="TemplateComp",
            round_name=f"{template_name}_round",
        )
        spec = CompetitionSpec.from_dict(payload)
        report = validate_competition_spec(spec)

        assert spec.name == "TemplateComp"
        assert spec.round_name == f"{template_name}_round"
        assert report.counts_by_severity()["error"] == 0


def test_example_future_specs_validate_without_errors() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    example_paths = [
        repo_root / "configs" / "examples" / "future_derivative_round.json",
        repo_root / "configs" / "examples" / "future_linked_round.json",
        repo_root / "configs" / "examples" / "future_signal_participant_round.json",
        repo_root / "configs" / "examples" / "future_conversion_auction_round.json",
    ]

    for example_path in example_paths:
        payload = json.loads(example_path.read_text())
        spec = CompetitionSpec.from_dict(payload)
        report = validate_competition_spec(spec)

        assert spec.products
        assert report.counts_by_severity()["error"] == 0
