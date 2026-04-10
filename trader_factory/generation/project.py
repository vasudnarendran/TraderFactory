from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from trader_factory.core.registry import recommend_capabilities
from trader_factory.core.specs import CompetitionSpec
from trader_factory.generation.bootstrap import render_markdown_plan


@dataclass(slots=True)
class TraderProjectResult:
    project_name: str
    output_dir: Path
    readme_path: Path
    spec_copy_path: Path
    plan_path: Path
    trader_path: Path
    params_path: Path
    notes_path: Path


def _project_slug(spec: CompetitionSpec) -> str:
    slug = f"{spec.name}_{spec.round_name}".strip("_").lower()
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in slug)


def _product_class_name(symbol: str) -> str:
    cleaned = "".join(char if char.isalnum() else "_" for char in symbol.title())
    return f"{cleaned}Trader"


def _render_params(spec: CompetitionSpec) -> str:
    lines = [
        "from __future__ import annotations",
        "",
        "# Generated baseline parameter scaffold.",
        "",
        "PRODUCT_LIMITS = {",
    ]
    for product in spec.products:
        lines.append(f'    "{product.symbol}": {product.position_limit},')
    lines += [
        "}",
        "",
        "PRODUCT_METADATA = {",
    ]
    for product in spec.products:
        capabilities = [cap.name for cap in recommend_capabilities(product)]
        lines += [
            f'    "{product.symbol}": {{',
            f'        "tick_size": {product.tick_size},',
            f'        "price_regime": "{product.price_regime}",',
            f'        "execution_style": "{product.execution_style}",',
            f'        "mechanics": {json.dumps(product.mechanics)},',
            f'        "recommended_capabilities": {json.dumps(capabilities)},',
            "    },",
        ]
    lines += [
        "}",
        "",
        "PRODUCT_PARAMS = {",
    ]
    for product in spec.products:
        lines += [
            f'    "{product.symbol}": {{',
            '        "ENABLED": True,',
            '        "BASE_TAKE_EDGE": 1.0,',
            '        "BASE_QUOTE_EDGE": 2.0,',
            '        "INVENTORY_SKEW": 0.0,',
            "    },",
        ]
    lines += [
        "}",
        "",
    ]
    return "\n".join(lines)


def _render_trader(spec: CompetitionSpec) -> str:
    product_setup_lines = []
    product_class_blocks = []
    for product in spec.products:
        class_name = _product_class_name(product.symbol)
        capabilities = [cap.name for cap in recommend_capabilities(product)]
        capability_comment = ", ".join(capabilities) if capabilities else "manual review needed"
        mechanics_comment = ", ".join(product.mechanics) if product.mechanics else "none declared"
        product_setup_lines.append(
            f'            "{product.symbol}": {class_name}("{product.symbol}", PRODUCT_LIMITS["{product.symbol}"], PRODUCT_PARAMS["{product.symbol}"]),'
        )
        product_class_blocks.extend(
            [
                f"class {class_name}(BaseProductTrader):",
                f"    # Recommended capabilities: {capability_comment}",
                f"    # Mechanics: {mechanics_comment}",
                "    def build_orders(self, state: TradingState) -> list[Order]:",
                "        # TODO: implement the product sleeve for this product.",
                "        return []",
                "",
            ]
        )

    lines = [
        "from __future__ import annotations",
        "",
        "from typing import Dict, List",
        "",
        "try:",
        "    from datamodel import Order, TradingState",
        "except ModuleNotFoundError:",
        "    from trader_factory.core.datamodel import Order, TradingState",
        "",
        "from params import PRODUCT_LIMITS, PRODUCT_PARAMS",
        "",
        "",
        "class BaseProductTrader:",
        "    def __init__(self, product: str, position_limit: int, params: dict) -> None:",
        "        self.product = product",
        "        self.position_limit = position_limit",
        "        self.params = params",
        "",
        "    def current_position(self, state: TradingState) -> int:",
        "        return int(state.position.get(self.product, 0))",
        "",
        "    def build_orders(self, state: TradingState) -> list[Order]:",
        "        raise NotImplementedError",
        "",
        *product_class_blocks,
        "class Trader:",
        "    def __init__(self) -> None:",
        "        self.product_traders: Dict[str, BaseProductTrader] = {",
        *product_setup_lines,
        "        }",
        "",
        "    def run(self, state: TradingState):",
        "        orders: Dict[str, List[Order]] = {}",
        "        for product, trader in self.product_traders.items():",
        "            if product in state.order_depths:",
        "                product_orders = trader.build_orders(state)",
        "                if product_orders:",
        "                    orders[product] = product_orders",
        '        return orders, 0, state.traderData if hasattr(state, "traderData") else ""',
        "",
    ]
    return "\n".join(lines)


def _render_readme(spec: CompetitionSpec, project_name: str) -> str:
    lines = [
        f"# {project_name}",
        "",
        f"Generated baseline trader project for `{spec.name}` / `{spec.round_name}`.",
        "",
        "## Files",
        "",
        "- `spec.json`: copied competition specification",
        "- `plan.md`: generated round plan and capability recommendations",
        "- `params.py`: baseline parameters and metadata",
        "- `trader.py`: runnable multi-product baseline scaffold",
        "- `notes.md`: room for round-specific discoveries and handoff notes",
        "",
        "## Working Rule",
        "",
        "- start with the generated baseline",
        "- validate with deterministic replay",
        "- validate with Monte Carlo robustness",
        "- only then optimize or switch into research mode",
        "",
    ]
    return "\n".join(lines)


def _render_notes(spec: CompetitionSpec) -> str:
    lines = [
        "# Notes",
        "",
        "Use this file to record round-specific discoveries.",
        "",
        "Initial checklist:",
        "- confirm product mechanics against the actual competition brief",
        "- confirm which recommended capabilities should really be in the baseline",
        "- define what success looks like for the first deterministic replay",
        "- decide whether the next step is development mode or research mode",
        "",
        "Products:",
    ]
    for product in spec.products:
        lines.append(f"- {product.symbol}: {product.notes or 'no extra notes yet'}")
    lines.append("")
    return "\n".join(lines)


def scaffold_trader_project(
    spec_path: str | Path,
    *,
    output_dir: str | Path | None = None,
    project_name: str | None = None,
) -> TraderProjectResult:
    spec_file = Path(spec_path).expanduser().resolve()
    spec = CompetitionSpec.from_json(spec_file)
    name = project_name or _project_slug(spec)
    workspace = Path(output_dir).expanduser().resolve() if output_dir else (Path.cwd() / name).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    readme_path = workspace / "README.md"
    spec_copy_path = workspace / "spec.json"
    plan_path = workspace / "plan.md"
    trader_path = workspace / "trader.py"
    params_path = workspace / "params.py"
    notes_path = workspace / "notes.md"

    readme_path.write_text(_render_readme(spec, name) + "\n")
    spec_copy_path.write_text(json.dumps(json.loads(spec_file.read_text()), indent=2) + "\n")
    plan_path.write_text(render_markdown_plan(spec))
    trader_path.write_text(_render_trader(spec))
    params_path.write_text(_render_params(spec))
    notes_path.write_text(_render_notes(spec))

    return TraderProjectResult(
        project_name=name,
        output_dir=workspace,
        readme_path=readme_path,
        spec_copy_path=spec_copy_path,
        plan_path=plan_path,
        trader_path=trader_path,
        params_path=params_path,
        notes_path=notes_path,
    )
