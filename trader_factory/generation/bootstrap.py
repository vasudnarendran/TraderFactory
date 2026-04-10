from __future__ import annotations

from dataclasses import dataclass, field

from trader_factory.core.registry import recommend_capabilities
from trader_factory.core.specs import CompetitionSpec


@dataclass(slots=True)
class ProductBuildPlan:
    symbol: str
    regime: str
    execution_style: str
    recommended_capabilities: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RoundBuildPlan:
    competition_name: str
    round_name: str
    products: list[ProductBuildPlan] = field(default_factory=list)
    global_notes: list[str] = field(default_factory=list)


def build_round_plan(spec: CompetitionSpec) -> RoundBuildPlan:
    plans: list[ProductBuildPlan] = []
    for product in spec.products:
        recommendations = recommend_capabilities(product)
        notes = [
            f"Mechanics: {', '.join(product.mechanics) if product.mechanics else 'none declared'}",
            f"Position limit: {product.position_limit}",
            f"Tick size: {product.tick_size}",
        ]
        if product.notes:
            notes.append(product.notes)
        plans.append(
            ProductBuildPlan(
                symbol=product.symbol,
                regime=product.price_regime,
                execution_style=product.execution_style,
                recommended_capabilities=[cap.name for cap in recommendations],
                notes=notes,
            )
        )

    global_notes = [
        "Start with a readable baseline per product before optimization.",
        "Use development mode for model building and optimization.",
        "Use research mode when local and official behavior diverge.",
    ]
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
        lines.append("- Recommended capabilities:")
        if product.recommended_capabilities:
            for name in product.recommended_capabilities:
                lines.append(f"  - `{name}`")
        else:
            lines.append("  - none matched; manual review needed")
        lines.append("- Notes:")
        for note in product.notes:
            lines.append(f"  - {note}")
    lines.append("")
    lines.append("## Global Notes")
    for note in plan.global_notes:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"

