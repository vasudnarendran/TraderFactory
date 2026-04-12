from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trader_factory.generation.spec_templates import render_spec_template


def _clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = [value]
    return [str(item).strip() for item in items if str(item).strip()]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    cleaned: dict[str, Any] = {}
    for key, raw in value.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            continue
        cleaned[normalized_key] = raw
    return cleaned


def _clean_sequence_of_mappings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            cleaned.append(dict(item))
    return cleaned


def _prune_empty(value: Any) -> Any:
    if isinstance(value, dict):
        pruned: dict[str, Any] = {}
        for key, raw in value.items():
            cleaned = _prune_empty(raw)
            if cleaned in ({}, [], "", None):
                continue
            pruned[key] = cleaned
        return pruned
    if isinstance(value, list):
        pruned_list = [_prune_empty(item) for item in value]
        return [item for item in pruned_list if item not in ({}, [], "", None)]
    return value


def _brief_product_from_spec_product(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": product.get("symbol", ""),
        "position_limit": product.get("position_limit", 0),
        "tick_size": product.get("tick_size", 1.0),
        "price_regime": product.get("price_regime", "unknown"),
        "execution_style": product.get("execution_style", "mixed"),
        "mechanic_hypotheses": list(product.get("mechanics", [])),
        "unknown_mechanics": list(product.get("unknown_mechanics", [])),
        "observations": list(product.get("observations", [])),
        "observation_channels": list(product.get("observation_channels", [])),
        "derivative_contract": dict(product.get("derivative_contract", {})),
        "conversion_rule": dict(product.get("conversion_rule", {})),
        "auction_rule": dict(product.get("auction_rule", {})),
        "basket_definition": dict(product.get("basket_definition", {})),
        "participant_rule": dict(product.get("participant_rule", {})),
        "signal_rule": dict(product.get("signal_rule", {})),
        "special_rules": list(product.get("special_rules", [])),
        "open_questions": list(product.get("open_questions", [])),
        "notes": product.get("notes", ""),
        "raw_brief_excerpt": "",
        "source_notes": [],
        "custom_fields": dict(product.get("custom_fields", {})),
    }


def render_round_brief_template(
    profile: str,
    *,
    competition_name: str = "NewCompetition",
    round_name: str = "round_1",
) -> dict[str, Any]:
    base_spec = render_spec_template(
        profile,
        competition_name=competition_name,
        round_name=round_name,
    )
    return {
        "competition_name": base_spec["name"],
        "round_name": base_spec["round_name"],
        "profile": profile,
        "summary": base_spec.get("description", ""),
        "sources": [],
        "raw_brief_excerpt": "",
        "mechanic_notes": list(base_spec.get("mechanics", [])),
        "products": [_brief_product_from_spec_product(product) for product in base_spec.get("products", [])],
        "relationships": list(base_spec.get("relationships", [])),
        "special_rules": list(base_spec.get("special_rules", [])),
        "constraints": list(base_spec.get("constraints", [])),
        "open_questions": list(base_spec.get("open_questions", [])),
        "unknown_mechanics": list(base_spec.get("unknown_mechanics", [])),
        "research_goals": list(base_spec.get("research_goals", [])),
    }


def extract_spec_from_brief(data: dict[str, Any]) -> dict[str, Any]:
    products: list[dict[str, Any]] = []
    for raw_product in data.get("products", []):
        product = _clean_mapping(raw_product)
        structured_product = {
            "symbol": _clean_text(product.get("symbol")),
            "position_limit": product.get("position_limit", 0),
            "tick_size": product.get("tick_size", 1.0),
            "price_regime": _clean_text(product.get("price_regime")) or "unknown",
            "execution_style": _clean_text(product.get("execution_style")) or "mixed",
            "mechanics": _clean_list(product.get("mechanic_hypotheses") or product.get("mechanics")),
            "unknown_mechanics": _clean_list(product.get("unknown_mechanics")),
            "observations": _clean_list(product.get("observations")),
            "observation_channels": _clean_sequence_of_mappings(product.get("observation_channels")),
            "basket_definition": _clean_mapping(product.get("basket_definition")),
            "participant_rule": _clean_mapping(product.get("participant_rule")),
            "signal_rule": _clean_mapping(product.get("signal_rule")),
            "derivative_contract": _clean_mapping(product.get("derivative_contract")),
            "conversion_rule": _clean_mapping(product.get("conversion_rule")),
            "auction_rule": _clean_mapping(product.get("auction_rule")),
            "special_rules": _clean_list(product.get("special_rules")),
            "open_questions": _clean_list(product.get("open_questions")),
            "notes": _clean_text(product.get("notes")),
            "custom_fields": _clean_mapping(product.get("custom_fields")),
        }
        products.append(_prune_empty(structured_product))

    spec = {
        "name": _clean_text(data.get("competition_name") or data.get("name")),
        "round_name": _clean_text(data.get("round_name")),
        "description": _clean_text(data.get("summary") or data.get("description")),
        "mechanics": _clean_sequence_of_mappings(data.get("mechanic_notes") or data.get("mechanics")),
        "products": products,
        "relationships": _clean_sequence_of_mappings(data.get("relationships")),
        "special_rules": _clean_sequence_of_mappings(data.get("special_rules")),
        "constraints": _clean_list(data.get("constraints")),
        "open_questions": _clean_list(data.get("open_questions")),
        "unknown_mechanics": _clean_list(data.get("unknown_mechanics")),
        "research_goals": _clean_list(data.get("research_goals")),
    }
    return _prune_empty(spec)


def _render_intake_workspace_readme(profile: str) -> str:
    lines = [
        "# Intake Workspace",
        "",
        "This workspace is the bridge between a raw round brief and a validated competition spec.",
        "",
        "## Files",
        "",
        "- `raw_brief.md`: paste or summarize the raw round brief here",
        "- `round_brief.json`: structured intake workbook for the round",
        "- `spec.json`: machine-readable spec generated from `round_brief.json`",
        "",
        "## Workflow",
        "",
        "1. Paste the raw round brief into `raw_brief.md`.",
        "2. Fill `round_brief.json` with concrete facts, mechanic hypotheses, and open questions.",
        "3. Regenerate the spec:",
        "",
        "```bash",
        "python3 -m trader_factory.cli brief-to-spec ./round_brief.json --output ./spec.json",
        "```",
        "",
        "4. Validate the spec:",
        "",
        "```bash",
        "python3 -m trader_factory.cli validate-spec ./spec.json",
        "```",
        "",
        "5. Scaffold only after blocked findings are fixed:",
        "",
        "```bash",
        "python3 -m trader_factory.cli scaffold-project ./spec.json",
        "```",
        "",
        f"Selected profile: `{profile}`.",
    ]
    return "\n".join(lines) + "\n"


@dataclass(slots=True)
class BriefWorkspaceResult:
    output_dir: Path
    raw_brief_path: Path
    round_brief_path: Path
    spec_path: Path
    readme_path: Path


def create_intake_workspace(
    profile: str,
    *,
    competition_name: str = "NewCompetition",
    round_name: str = "round_1",
    output_dir: str | Path | None = None,
) -> BriefWorkspaceResult:
    workspace = Path(output_dir).expanduser().resolve() if output_dir else (Path.cwd() / f"{round_name}_intake").resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    readme_path = workspace / "README.md"
    raw_brief_path = workspace / "raw_brief.md"
    round_brief_path = workspace / "round_brief.json"
    spec_path = workspace / "spec.json"

    round_brief = render_round_brief_template(
        profile,
        competition_name=competition_name,
        round_name=round_name,
    )
    spec = extract_spec_from_brief(round_brief)

    readme_path.write_text(_render_intake_workspace_readme(profile))
    raw_brief_path.write_text(
        "# Raw Brief\n\nPaste the round brief, rules summary, or copied notes here before you fill `round_brief.json`.\n"
    )
    round_brief_path.write_text(json.dumps(round_brief, indent=2) + "\n")
    spec_path.write_text(json.dumps(spec, indent=2) + "\n")

    return BriefWorkspaceResult(
        output_dir=workspace,
        raw_brief_path=raw_brief_path,
        round_brief_path=round_brief_path,
        spec_path=spec_path,
        readme_path=readme_path,
    )
