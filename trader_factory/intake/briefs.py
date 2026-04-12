from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
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


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        cleaned = str(item).strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        ordered.append(cleaned)
    return ordered


def _contains_any(text: str, phrases: list[str]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def _question_candidates(texts: list[str]) -> list[str]:
    questions: list[str] = []
    for text in texts:
        normalized = _clean_text(text)
        if not normalized:
            continue
        if "?" in normalized:
            for chunk in normalized.split("?"):
                question = chunk.strip()
                if question:
                    questions.append(question + "?")
    return _unique(questions)


def _normalize_symbol_token(value: str) -> str:
    return re.sub(r"[^A-Z0-9_]", "", value.upper())


def _symbols_mentioned_in_text(text: str, symbols: set[str], *, exclude: str = "") -> list[str]:
    mentioned: list[str] = []
    normalized_text = text.upper()
    for symbol in sorted(symbols):
        if symbol == exclude:
            continue
        pattern = re.compile(rf"(?<![A-Z0-9_]){re.escape(symbol)}(?![A-Z0-9_])")
        if pattern.search(normalized_text):
            mentioned.append(symbol)
    return mentioned


MECHANIC_TEXT_RULES: list[tuple[list[str], list[str]]] = [
    (["stable fair", "fixed fair", "anchored", "pegged"], ["anchored", "static_anchor", "stable_fair"]),
    (["market making", "quote around", "spread capture", "maker"], ["market_making"]),
    (["inventory", "position pressure"], ["inventory_sensitive"]),
    (["trend", "momentum"], ["trend"]),
    (["mean reversion", "reversion"], ["mean_reversion"]),
    (["imbalance", "microstructure", "order book", "flow pressure"], ["microstructure_alpha"]),
    (["breakout", "burst"], ["breakout"]),
    (["linked", "relative value", "pair"], ["pair_linked"]),
    (["spread"], ["spread_relationship"]),
    (["basket", "components", "bundle"], ["basket"]),
    (["option", "call", "put", "strike"], ["option", "derivative"]),
    (["expiry", "expires", "maturity"], ["expiry"]),
    (["settlement formula", "settles to", "settlement"], ["settlement_formula"]),
    (["convert", "conversion"], ["conversion"]),
    (["transport", "shipping", "tariff", "import", "export"], ["transport"]),
    (["auction", "clearing", "indicative price", "imbalance"], ["auction"]),
    (["signal", "weather", "sunlight", "humidity", "satellite", "feed"], ["external_signal"]),
    (["participant", "named trader"], ["named_participant"]),
    (["flow following", "follow flow", "fade flow"], ["flow_following"]),
    (["informed trader"], ["informed_trader"]),
    (["official simulator", "passive fill", "queue"], ["unknown_execution"]),
    (["hidden simulator"], ["hidden_simulator"]),
    (["transfer gap"], ["transfer_gap"]),
    (["thin liquidity"], ["thin_liquidity"]),
    (["impact", "slippage"], ["impact_sensitive"]),
]


@dataclass(slots=True)
class ExtractionNote:
    scope: str
    subject: str
    field: str
    message: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "subject": self.subject,
            "field": self.field,
            "message": self.message,
            "evidence": list(self.evidence),
        }


@dataclass(slots=True)
class BriefExtractionReport:
    competition_name: str
    round_name: str
    notes: list[ExtractionNote] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "competition_name": self.competition_name,
            "round_name": self.round_name,
            "notes": [note.to_dict() for note in self.notes],
        }


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
        "underlying_hint": "",
        "related_products_hint": [],
        "relationship_style_hint": "",
        "target_product_hint": "",
        "source_product_hint": "",
        "signal_source_hint": "",
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


def _product_text_blobs(product: dict[str, Any]) -> list[str]:
    texts = [
        _clean_text(product.get("notes")),
        _clean_text(product.get("raw_brief_excerpt")),
        *_clean_list(product.get("source_notes")),
        *_clean_list(product.get("observations")),
        *_clean_list(product.get("special_rules")),
    ]
    return [text for text in texts if text]


def _round_text_blobs(data: dict[str, Any]) -> list[str]:
    texts = [
        _clean_text(data.get("summary") or data.get("description")),
        _clean_text(data.get("raw_brief_excerpt")),
        *_clean_list(data.get("constraints")),
        *_clean_list(data.get("open_questions")),
        *_clean_list(data.get("unknown_mechanics")),
        *_clean_list(data.get("research_goals")),
    ]
    return [text for text in texts if text]


def _add_note(report: BriefExtractionReport, *, scope: str, subject: str, field_name: str, message: str, evidence: list[str]) -> None:
    report.notes.append(
        ExtractionNote(
            scope=scope,
            subject=subject,
            field=field_name,
            message=message,
            evidence=_unique(evidence),
        )
    )


def _infer_mechanics_from_text(product: dict[str, Any], known_symbols: set[str]) -> tuple[list[str], list[tuple[str, list[str]]]]:
    texts = _product_text_blobs(product)
    combined = " | ".join(texts).lower()
    inferred: list[str] = []
    evidence_notes: list[tuple[str, list[str]]] = []
    for phrases, mechanics in MECHANIC_TEXT_RULES:
        if _contains_any(combined, phrases):
            inferred.extend(mechanics)
            evidence_notes.append((", ".join(mechanics), phrases))

    symbol = _normalize_symbol_token(_clean_text(product.get("symbol")))
    mentioned_symbols = _symbols_mentioned_in_text(" ".join(texts), known_symbols, exclude=symbol)
    if mentioned_symbols and any(mechanic in inferred for mechanic in ("option", "derivative", "conversion", "pair_linked", "spread_relationship", "basket")):
        inferred.append("pair_linked")
        evidence_notes.append(("pair_linked", mentioned_symbols))
    return _unique(inferred), evidence_notes


def _ensure_signal_channel(
    observation_channels: list[dict[str, Any]],
    signal_key: str,
    report: BriefExtractionReport,
    symbol: str,
) -> list[dict[str, Any]]:
    if not signal_key:
        return observation_channels
    for channel in observation_channels:
        if _clean_text(channel.get("key")) == signal_key:
            return observation_channels
    updated = list(observation_channels)
    updated.append(
        {
            "key": signal_key,
            "kind": "plain",
            "role": "signal",
            "description": "Auto-created from the structured brief signal source hint.",
        }
    )
    _add_note(
        report,
        scope="product",
        subject=symbol,
        field_name="observation_channels",
        message=f"Created a plain signal observation channel for `{signal_key}` because the brief declared a signal source without an explicit channel.",
        evidence=[signal_key],
    )
    return updated


def _infer_price_regime(
    explicit: str,
    mechanics: list[str],
    product_text: list[str],
) -> tuple[str, list[str]] | None:
    cleaned = _clean_text(explicit)
    if cleaned and cleaned != "unknown":
        return None
    mechanic_set = set(mechanics)
    evidence = list(product_text)
    if mechanic_set & {"option", "derivative", "expiry", "nonlinear_payoff"}:
        return "derivative", evidence
    if mechanic_set & {"basket", "pair_linked", "spread_relationship"}:
        return "linked", evidence
    if "auction" in mechanic_set:
        return "auction", evidence
    if mechanic_set & {"anchored", "static_anchor", "stable_fair"}:
        return "anchored", evidence
    if mechanic_set:
        return "mixed", evidence
    return None


def _infer_execution_style(explicit: str, product_text: list[str]) -> tuple[str, list[str]] | None:
    cleaned = _clean_text(explicit).lower()
    if cleaned and cleaned != "unknown":
        return None
    combined = " | ".join(product_text).lower()
    has_passive = _contains_any(combined, ["passive", "maker", "quote", "quoting", "join the book"])
    has_aggressive = _contains_any(combined, ["aggressive", "taker", "cross the spread", "take liquidity"])
    if has_passive and not has_aggressive:
        return "mostly_passive", product_text
    if has_aggressive and not has_passive:
        return "mostly_aggressive", product_text
    if has_passive or has_aggressive:
        return "mixed", product_text
    return None


def _derive_relationships_from_hints(products: list[dict[str, Any]], known_symbols: set[str], report: BriefExtractionReport) -> list[dict[str, Any]]:
    derived: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for product in products:
        symbol = _clean_text(product.get("symbol"))
        related_hints = [_normalize_symbol_token(item) for item in _clean_list(product.get("related_products_hint"))]
        relationship_style = _clean_text(product.get("relationship_style_hint")) or "linked"
        for counterpart in related_hints:
            if not counterpart or counterpart not in known_symbols or counterpart == symbol:
                continue
            key = tuple(sorted((symbol, counterpart))) + (relationship_style,)
            if key in seen:
                continue
            seen.add(key)
            relationship = {
                "left": symbol,
                "right": counterpart,
                "relationship": relationship_style,
                "description": "Auto-created from the structured brief related-products hint.",
            }
            derived.append(relationship)
            _add_note(
                report,
                scope="round",
                subject=symbol,
                field_name="relationships",
                message=f"Created a `{relationship_style}` relationship between `{symbol}` and `{counterpart}` from brief hints.",
                evidence=[symbol, counterpart],
            )
    return derived


def extract_spec_with_report(data: dict[str, Any]) -> tuple[dict[str, Any], BriefExtractionReport]:
    competition_name = _clean_text(data.get("competition_name") or data.get("name"))
    round_name = _clean_text(data.get("round_name"))
    report = BriefExtractionReport(competition_name=competition_name, round_name=round_name)
    known_symbols = {
        _normalize_symbol_token(_clean_text(product.get("symbol")))
        for product in data.get("products", [])
        if _clean_text(product.get("symbol"))
    }

    products: list[dict[str, Any]] = []
    brief_products = [_clean_mapping(product) for product in data.get("products", [])]
    for raw_product in brief_products:
        symbol = _clean_text(raw_product.get("symbol"))
        normalized_symbol = _normalize_symbol_token(symbol)
        product_text = _product_text_blobs(raw_product)

        mechanics = _clean_list(raw_product.get("mechanic_hypotheses") or raw_product.get("mechanics"))
        inferred_mechanics, inference_rules = _infer_mechanics_from_text(raw_product, known_symbols)
        for inferred in inferred_mechanics:
            if inferred not in mechanics:
                mechanics.append(inferred)
        if inferred_mechanics:
            for mechanic_label, evidence in inference_rules:
                _add_note(
                    report,
                    scope="product",
                    subject=symbol,
                    field_name="mechanics",
                    message=f"Inferred mechanic label(s) `{mechanic_label}` from brief text.",
                    evidence=evidence,
                )

        derivative_contract = _clean_mapping(raw_product.get("derivative_contract"))
        if not derivative_contract.get("underlying"):
            underlying_hint = _normalize_symbol_token(_clean_text(raw_product.get("underlying_hint")))
            if underlying_hint:
                derivative_contract["underlying"] = underlying_hint
                _add_note(
                    report,
                    scope="product",
                    subject=symbol,
                    field_name="derivative_contract.underlying",
                    message=f"Filled derivative underlying from `underlying_hint` as `{underlying_hint}`.",
                    evidence=[underlying_hint],
                )
            elif any(mechanic in mechanics for mechanic in ("option", "derivative")):
                mentioned = _symbols_mentioned_in_text(" ".join(product_text), known_symbols, exclude=normalized_symbol)
                if len(mentioned) == 1:
                    derivative_contract["underlying"] = mentioned[0]
                    _add_note(
                        report,
                        scope="product",
                        subject=symbol,
                        field_name="derivative_contract.underlying",
                        message=f"Inferred derivative underlying as `{mentioned[0]}` from brief text symbol references.",
                        evidence=mentioned,
                    )

        conversion_rule = _clean_mapping(raw_product.get("conversion_rule"))
        if not conversion_rule.get("target_product"):
            target_hint = _normalize_symbol_token(_clean_text(raw_product.get("target_product_hint")))
            if target_hint:
                conversion_rule["target_product"] = target_hint
                _add_note(
                    report,
                    scope="product",
                    subject=symbol,
                    field_name="conversion_rule.target_product",
                    message=f"Filled conversion target product from `target_product_hint` as `{target_hint}`.",
                    evidence=[target_hint],
                )
        if not conversion_rule.get("source_product"):
            source_hint = _normalize_symbol_token(_clean_text(raw_product.get("source_product_hint")))
            if source_hint:
                conversion_rule["source_product"] = source_hint
                _add_note(
                    report,
                    scope="product",
                    subject=symbol,
                    field_name="conversion_rule.source_product",
                    message=f"Filled conversion source product from `source_product_hint` as `{source_hint}`.",
                    evidence=[source_hint],
                )

        signal_rule = _clean_mapping(raw_product.get("signal_rule"))
        signal_source_hint = _clean_text(raw_product.get("signal_source_hint"))
        if not signal_rule.get("source_key"):
            if signal_source_hint:
                signal_rule["source_key"] = signal_source_hint
                _add_note(
                    report,
                    scope="product",
                    subject=symbol,
                    field_name="signal_rule.source_key",
                    message=f"Filled signal source key from `signal_source_hint` as `{signal_source_hint}`.",
                    evidence=[signal_source_hint],
                )
            else:
                observation_channels = _clean_sequence_of_mappings(raw_product.get("observation_channels"))
                signal_candidates = [
                    _clean_text(channel.get("key"))
                    for channel in observation_channels
                    if _clean_text(channel.get("role")).lower() == "signal" and _clean_text(channel.get("key"))
                ]
                if len(signal_candidates) == 1:
                    signal_rule["source_key"] = signal_candidates[0]
                    _add_note(
                        report,
                        scope="product",
                        subject=symbol,
                        field_name="signal_rule.source_key",
                        message=f"Inferred signal source key as `{signal_candidates[0]}` from the only signal-tagged observation channel.",
                        evidence=signal_candidates,
                    )

        observation_channels = _clean_sequence_of_mappings(raw_product.get("observation_channels"))
        if signal_rule.get("source_key"):
            observation_channels = _ensure_signal_channel(observation_channels, _clean_text(signal_rule["source_key"]), report, symbol)

        price_regime = _clean_text(raw_product.get("price_regime")) or "unknown"
        regime_inference = _infer_price_regime(price_regime, mechanics, product_text)
        if regime_inference is not None:
            price_regime, evidence = regime_inference
            _add_note(
                report,
                scope="product",
                subject=symbol,
                field_name="price_regime",
                message=f"Inferred `price_regime` as `{price_regime}` from mechanics and brief text.",
                evidence=evidence[:3],
            )

        execution_style = _clean_text(raw_product.get("execution_style")) or "mixed"
        execution_inference = _infer_execution_style(execution_style, product_text)
        if execution_inference is not None:
            execution_style, evidence = execution_inference
            _add_note(
                report,
                scope="product",
                subject=symbol,
                field_name="execution_style",
                message=f"Inferred `execution_style` as `{execution_style}` from brief text.",
                evidence=evidence[:3],
            )

        open_questions = _clean_list(raw_product.get("open_questions"))
        inferred_questions = _question_candidates([
            _clean_text(raw_product.get("raw_brief_excerpt")),
            *_clean_list(raw_product.get("source_notes")),
        ])
        for question in inferred_questions:
            if question not in open_questions:
                open_questions.append(question)
                _add_note(
                    report,
                    scope="product",
                    subject=symbol,
                    field_name="open_questions",
                    message=f"Captured an explicit question from the brief text for `{symbol}`.",
                    evidence=[question],
                )

        structured_product = {
            "symbol": symbol,
            "position_limit": raw_product.get("position_limit", 0),
            "tick_size": raw_product.get("tick_size", 1.0),
            "price_regime": price_regime,
            "execution_style": execution_style,
            "mechanics": _unique(mechanics),
            "unknown_mechanics": _clean_list(raw_product.get("unknown_mechanics")),
            "observations": _clean_list(raw_product.get("observations")),
            "observation_channels": observation_channels,
            "basket_definition": _clean_mapping(raw_product.get("basket_definition")),
            "participant_rule": _clean_mapping(raw_product.get("participant_rule")),
            "signal_rule": signal_rule,
            "derivative_contract": derivative_contract,
            "conversion_rule": conversion_rule,
            "auction_rule": _clean_mapping(raw_product.get("auction_rule")),
            "special_rules": _clean_list(raw_product.get("special_rules")),
            "open_questions": open_questions,
            "notes": _clean_text(raw_product.get("notes")),
            "custom_fields": _clean_mapping(raw_product.get("custom_fields")),
        }
        products.append(_prune_empty(structured_product))

    spec = {
        "name": competition_name,
        "round_name": round_name,
        "description": _clean_text(data.get("summary") or data.get("description")),
        "mechanics": _clean_sequence_of_mappings(data.get("mechanic_notes") or data.get("mechanics")),
        "products": products,
        "relationships": _clean_sequence_of_mappings(data.get("relationships")) + _derive_relationships_from_hints(brief_products, known_symbols, report),
        "special_rules": _clean_sequence_of_mappings(data.get("special_rules")),
        "constraints": _clean_list(data.get("constraints")),
        "open_questions": _unique(
            _clean_list(data.get("open_questions"))
            + _question_candidates([
                _clean_text(data.get("raw_brief_excerpt")),
                *_clean_list(data.get("constraints")),
            ])
        ),
        "unknown_mechanics": _clean_list(data.get("unknown_mechanics")),
        "research_goals": _clean_list(data.get("research_goals")),
    }
    return _prune_empty(spec), report


def extract_spec_from_brief(data: dict[str, Any]) -> dict[str, Any]:
    spec, _report = extract_spec_with_report(data)
    return spec


def render_extraction_markdown(report: BriefExtractionReport) -> str:
    lines = [
        f"# Brief Extraction Report: {report.competition_name} / {report.round_name}",
        "",
        f"- Inference notes: {len(report.notes)}",
        "",
    ]
    if not report.notes:
        lines.append("No inferred fields were recorded.")
        lines.append("")
        return "\n".join(lines)

    lines.append("## Notes")
    lines.append("")
    for note in report.notes:
        lines.append(f"- [{note.scope}] `{note.subject}` `{note.field}`: {note.message}")
        if note.evidence:
            lines.append(f"  Evidence: {', '.join(note.evidence)}")
    lines.append("")
    return "\n".join(lines)


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
        "- `brief_extraction.md`: transparent report of fields inferred during brief-to-spec extraction",
        "",
        "## Workflow",
        "",
        "1. Paste the raw round brief into `raw_brief.md`.",
        "2. Fill `round_brief.json` with concrete facts, helper hints, mechanic hypotheses, and open questions.",
        "3. Regenerate the spec:",
        "",
        "```bash",
        "python3 -m trader_factory.cli brief-to-spec ./round_brief.json --output ./spec.json --report-output ./brief_extraction.md",
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
    extraction_report_path: Path
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
    extraction_report_path = workspace / "brief_extraction.md"

    round_brief = render_round_brief_template(
        profile,
        competition_name=competition_name,
        round_name=round_name,
    )
    spec, report = extract_spec_with_report(round_brief)

    readme_path.write_text(_render_intake_workspace_readme(profile))
    raw_brief_path.write_text(
        "# Raw Brief\n\nPaste the round brief, rules summary, or copied notes here before you fill `round_brief.json`.\n"
    )
    round_brief_path.write_text(json.dumps(round_brief, indent=2) + "\n")
    spec_path.write_text(json.dumps(spec, indent=2) + "\n")
    extraction_report_path.write_text(render_extraction_markdown(report))

    return BriefWorkspaceResult(
        output_dir=workspace,
        raw_brief_path=raw_brief_path,
        round_brief_path=round_brief_path,
        spec_path=spec_path,
        extraction_report_path=extraction_report_path,
        readme_path=readme_path,
    )
