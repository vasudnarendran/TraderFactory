from __future__ import annotations

from dataclasses import dataclass, field

from trader_factory.core.mapping import interpret_competition
from trader_factory.core.specs import CompetitionSpec
from trader_factory.strategies import get_archetype_blueprint


@dataclass(slots=True)
class ProductBuildPlan:
    symbol: str
    regime: str
    execution_style: str
    preferred_archetype: str
    fallback_mode: str
    recommended_capabilities: list[str] = field(default_factory=list)
    capability_details: list[str] = field(default_factory=list)
    research_triggers: list[str] = field(default_factory=list)
    intake_gaps: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RoundBuildPlan:
    competition_name: str
    round_name: str
    products: list[ProductBuildPlan] = field(default_factory=list)
    global_notes: list[str] = field(default_factory=list)


def build_round_plan(spec: CompetitionSpec) -> RoundBuildPlan:
    plans: list[ProductBuildPlan] = []
    interpretations = interpret_competition(spec)
    for product in spec.products:
        interpretation = interpretations[product.symbol]
        recommendations = interpretation.recommended_capabilities
        notes = [
            f"Mechanics: {', '.join(product.mechanics) if product.mechanics else 'none declared'}",
            f"Position limit: {product.position_limit}",
            f"Tick size: {product.tick_size}",
        ]
        if interpretation.related_products:
            notes.append(f"Related products: {', '.join(interpretation.related_products)}")
        if interpretation.unknown_mechanics:
            notes.append(f"Unknown mechanics: {', '.join(interpretation.unknown_mechanics)}")
        if interpretation.special_rules:
            notes.append(f"Special rules: {', '.join(interpretation.special_rules)}")
        blueprint = get_archetype_blueprint(interpretation.preferred_archetype)
        if blueprint is not None:
            notes.append(f"Structural blueprint: {blueprint.summary}")
        if interpretation.warnings:
            notes.extend(interpretation.warnings)
        if product.notes:
            notes.append(product.notes)
        plans.append(
            ProductBuildPlan(
                symbol=product.symbol,
                regime=product.price_regime,
                execution_style=product.execution_style,
                preferred_archetype=interpretation.preferred_archetype,
                fallback_mode=interpretation.fallback_mode,
                recommended_capabilities=[cap.name for cap in recommendations],
                capability_details=[
                    f"{cap.name} [{', '.join(cap.families) or 'unclassified'} / {cap.readiness}] - {cap.summary}"
                    for cap in recommendations
                ],
                research_triggers=interpretation.research_triggers,
                intake_gaps=interpretation.intake_gaps,
                notes=notes,
            )
        )

    global_notes = [
        "Start with a readable baseline per product before optimization.",
        "Use development mode for model building and optimization.",
        "Use research mode when local and official behavior diverge.",
        "TraderFactory handles the mechanical mapping; the agent should spend time only on unresolved mechanics and strategy choices.",
        "Unknown mechanics are meant to stay explicit so the generated project can surface them for review instead of guessing.",
    ]
    if spec.relationships:
        global_notes.append(f"Declared relationships: {len(spec.relationships)}")
    if spec.special_rules:
        global_notes.append(
            "Special rules recorded: " + ", ".join(rule.name or rule.description for rule in spec.special_rules)
        )
    if spec.unknown_mechanics:
        global_notes.append(f"Round-level unknown mechanics: {', '.join(spec.unknown_mechanics)}")
    if spec.open_questions:
        global_notes.append(f"Round open questions: {', '.join(spec.open_questions)}")
    if spec.research_goals:
        global_notes.append(f"Research goals: {', '.join(spec.research_goals)}")
    return RoundBuildPlan(
        competition_name=spec.name,
        round_name=spec.round_name,
        products=plans,
        global_notes=global_notes,
    )


def render_markdown_plan(spec: CompetitionSpec) -> str:
    plan = build_round_plan(spec)
    lines: list[str] = []
    lines.append(f"# Round Plan: {plan.competition_name} / {plan.round_name}")
    if spec.description:
        lines.append("")
        lines.append(spec.description)
    lines.append("")
    lines.append("## Product Plans")
    for product in plan.products:
        lines.append("")
        lines.append(f"### {product.symbol}")
        lines.append(f"- Regime: `{product.regime}`")
        lines.append(f"- Execution style: `{product.execution_style}`")
        lines.append(f"- Preferred archetype: `{product.preferred_archetype}`")
        lines.append(f"- Fallback mode: `{product.fallback_mode}`")
        lines.append("- Recommended capabilities:")
        if product.capability_details:
            for detail in product.capability_details:
                name, rest = detail.split(" ", 1)
                lines.append(f"  - `{name}` {rest}")
        else:
            lines.append("  - none matched; manual review needed")
        lines.append("- Research triggers:")
        if product.research_triggers:
            for trigger in product.research_triggers:
                lines.append(f"  - `{trigger}`")
        else:
            lines.append("  - none from current mechanics")
        lines.append("- Intake gaps:")
        if product.intake_gaps:
            for gap in product.intake_gaps:
                lines.append(f"  - {gap}")
        else:
            lines.append("  - no immediate gaps from the current spec")
        lines.append("- Notes:")
        for note in product.notes:
            lines.append(f"  - {note}")
    lines.append("")
    lines.append("## Global Notes")
    for note in plan.global_notes:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"
