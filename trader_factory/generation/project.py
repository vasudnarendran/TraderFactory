from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trader_factory.core.registry import recommend_capabilities
from trader_factory.core.specs import CompetitionSpec, ProductSpec
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
    experiments_dir: Path
    research_dir: Path


def _project_slug(spec: CompetitionSpec) -> str:
    slug = f"{spec.name}_{spec.round_name}".strip("_").lower()
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in slug)


def _symbol_identifier(symbol: str) -> str:
    cleaned = "".join(char if char.isalnum() else "_" for char in symbol)
    return cleaned.strip("_") or "PRODUCT"


def _product_class_name(symbol: str) -> str:
    parts = [part for part in _symbol_identifier(symbol).split("_") if part]
    return "".join(part[:1].upper() + part[1:].lower() for part in parts) + "Trader"


def _params_block_name(symbol: str) -> str:
    return f"DEFAULT_{_symbol_identifier(symbol).upper()}_PARAMS"


def _capability_names(product: ProductSpec) -> list[str]:
    return [cap.name for cap in recommend_capabilities(product)]


def _choose_archetype(product: ProductSpec) -> str:
    capabilities = set(_capability_names(product))
    if "option_parity_and_hedging" in capabilities:
        return "derivative_stub"
    if "pair_or_spread_trading" in capabilities:
        return "spread_stub"
    if "informed_flow_tracking" in capabilities:
        return "participant_stub"
    if "static_anchor_mm" in capabilities:
        return "anchored_mm"
    if {
        "short_horizon_regression_alpha",
        "residual_mean_reversion",
        "breakout_confirmation",
    } & capabilities:
        return "directional_mm"
    if {"join_improve_mm", "inventory_skew_mm"} & capabilities:
        return "simple_mm"
    return "simple_mm"


def _python_literal(value: Any) -> str:
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, list):
        return json.dumps(value)
    if isinstance(value, dict):
        return json.dumps(value, indent=2)
    raise TypeError(f"Unsupported literal value: {value!r}")


def _default_param_items(product: ProductSpec, archetype: str) -> list[tuple[str, Any]]:
    passive_size = max(1, product.position_limit // 8)
    take_size = max(1, product.position_limit // 10)
    if archetype == "anchored_mm":
        return [
            ("ENABLED", True),
            ("ANCHOR_PRICE", None),
            ("TAKE_EDGE", 1.0),
            ("QUOTE_EDGE", 2.0),
            ("MAX_PASSIVE_SIZE", passive_size),
            ("MAX_TAKE_SIZE", take_size),
            ("INVENTORY_SKEW", 0.75),
        ]
    if archetype == "directional_mm":
        return [
            ("ENABLED", True),
            ("TAKE_EDGE", 0.9),
            ("QUOTE_EDGE", 1.7),
            ("MAX_PASSIVE_SIZE", max(1, product.position_limit // 10)),
            ("MAX_TAKE_SIZE", max(1, product.position_limit // 12)),
            ("IMBALANCE_SHIFT", 1.0),
            ("MICROPRICE_WEIGHT", 0.8),
            ("REVERSION_WEIGHT", 0.25 if "mean_reversion" in product.mechanics else 0.0),
            ("INVENTORY_SKEW", 0.5),
        ]
    if archetype == "simple_mm":
        return [
            ("ENABLED", True),
            ("TAKE_EDGE", 1.0),
            ("QUOTE_EDGE", 2.0),
            ("MAX_PASSIVE_SIZE", passive_size),
            ("MAX_TAKE_SIZE", take_size),
            ("INVENTORY_SKEW", 0.6),
        ]
    return [
        ("ENABLED", True),
        ("TODO_NOTE", f"Implement a {archetype} sleeve for {product.symbol} based on the round brief."),
    ]


def _render_params(spec: CompetitionSpec) -> str:
    lines = [
        "from __future__ import annotations",
        "",
        "# Generated project metadata scaffold.",
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
        capabilities = _capability_names(product)
        archetype = _choose_archetype(product)
        lines += [
            f'    "{product.symbol}": {{',
            f'        "tick_size": {product.tick_size},',
            f'        "price_regime": "{product.price_regime}",',
            f'        "execution_style": "{product.execution_style}",',
            f'        "mechanics": {json.dumps(product.mechanics)},',
            f'        "observations": {json.dumps(product.observations)},',
            f'        "recommended_capabilities": {json.dumps(capabilities)},',
            f'        "generated_archetype": "{archetype}",',
            "    },",
        ]
    lines += [
        "}",
        "",
    ]
    return "\n".join(lines)


def _render_param_blocks(spec: CompetitionSpec) -> list[str]:
    blocks: list[str] = []
    for product in spec.products:
        block_name = _params_block_name(product.symbol)
        blocks.append(f"{block_name} = {{")
        for key, value in _default_param_items(product, _choose_archetype(product)):
            blocks.append(f'    "{key}": {_python_literal(value)},')
        blocks.append("}")
        blocks.append("")
    return blocks


def _anchored_class_block(product: ProductSpec) -> list[str]:
    class_name = _product_class_name(product.symbol)
    block_name = _params_block_name(product.symbol)
    capability_comment = ", ".join(_capability_names(product)) or "manual review needed"
    mechanics_comment = ", ".join(product.mechanics) if product.mechanics else "none declared"
    return [
        f"class {class_name}(BaseProductTrader):",
        f"    # Archetype: anchored_mm",
        f"    # Recommended capabilities: {capability_comment}",
        f"    # Mechanics: {mechanics_comment}",
        "    def default_params(self) -> dict:",
        f"        return dict({block_name})",
        "",
        "    def build_orders(self, state: TradingState) -> list[Order]:",
        "        if not self.params.get(\"ENABLED\", True):",
        "            return []",
        "        touch = self.touch(state)",
        "        if touch is None:",
        "            return []",
        "        best_bid, bid_volume, best_ask, ask_volume = touch",
        "        position = self.current_position(state)",
        "        mid = self.mid_price(best_bid, best_ask)",
        "        anchor = self.params.get(\"ANCHOR_PRICE\")",
        "        fair = float(mid if anchor is None else anchor)",
        "        fair -= self.params.get(\"INVENTORY_SKEW\", 0.0) * self.inventory_ratio(position) * self.tick_size_value",
        "        orders: list[Order] = []",
        "        take_edge = float(self.params.get(\"TAKE_EDGE\", 1.0))",
        "        if best_ask <= fair - take_edge:",
        "            qty = min(self.take_size(position), self.buy_capacity(position), ask_volume)",
        "            if qty > 0:",
        "                orders.append(Order(self.product, best_ask, qty))",
        "        if best_bid >= fair + take_edge:",
        "            qty = min(self.take_size(position), self.sell_capacity(position), bid_volume)",
        "            if qty > 0:",
        "                orders.append(Order(self.product, best_bid, -qty))",
        "        self.add_passive_quotes(orders, fair, position, best_bid, best_ask)",
        "        return orders",
        "",
    ]


def _directional_class_block(product: ProductSpec) -> list[str]:
    class_name = _product_class_name(product.symbol)
    block_name = _params_block_name(product.symbol)
    capability_comment = ", ".join(_capability_names(product)) or "manual review needed"
    mechanics_comment = ", ".join(product.mechanics) if product.mechanics else "none declared"
    return [
        f"class {class_name}(BaseProductTrader):",
        f"    # Archetype: directional_mm",
        f"    # Recommended capabilities: {capability_comment}",
        f"    # Mechanics: {mechanics_comment}",
        "    def default_params(self) -> dict:",
        f"        return dict({block_name})",
        "",
        "    def build_orders(self, state: TradingState) -> list[Order]:",
        "        if not self.params.get(\"ENABLED\", True):",
        "            return []",
        "        touch = self.touch(state)",
        "        if touch is None:",
        "            return []",
        "        best_bid, bid_volume, best_ask, ask_volume = touch",
        "        position = self.current_position(state)",
        "        mid = self.mid_price(best_bid, best_ask)",
        "        micro = self.microprice(best_bid, bid_volume, best_ask, ask_volume)",
        "        imbalance = self.top_imbalance(bid_volume, ask_volume)",
        "        fair = mid",
        "        fair += self.params.get(\"IMBALANCE_SHIFT\", 0.0) * imbalance * self.tick_size_value",
        "        fair += self.params.get(\"MICROPRICE_WEIGHT\", 0.0) * (micro - mid)",
        "        fair += self.params.get(\"REVERSION_WEIGHT\", 0.0) * (mid - micro)",
        "        fair -= self.params.get(\"INVENTORY_SKEW\", 0.0) * self.inventory_ratio(position) * self.tick_size_value",
        "        orders: list[Order] = []",
        "        take_edge = float(self.params.get(\"TAKE_EDGE\", 1.0))",
        "        if best_ask <= fair - take_edge:",
        "            qty = min(self.take_size(position), self.buy_capacity(position), ask_volume)",
        "            if qty > 0:",
        "                orders.append(Order(self.product, best_ask, qty))",
        "        if best_bid >= fair + take_edge:",
        "            qty = min(self.take_size(position), self.sell_capacity(position), bid_volume)",
        "            if qty > 0:",
        "                orders.append(Order(self.product, best_bid, -qty))",
        "        self.add_passive_quotes(orders, fair, position, best_bid, best_ask)",
        "        return orders",
        "",
    ]


def _simple_mm_class_block(product: ProductSpec) -> list[str]:
    class_name = _product_class_name(product.symbol)
    block_name = _params_block_name(product.symbol)
    capability_comment = ", ".join(_capability_names(product)) or "manual review needed"
    mechanics_comment = ", ".join(product.mechanics) if product.mechanics else "none declared"
    return [
        f"class {class_name}(BaseProductTrader):",
        f"    # Archetype: simple_mm",
        f"    # Recommended capabilities: {capability_comment}",
        f"    # Mechanics: {mechanics_comment}",
        "    def default_params(self) -> dict:",
        f"        return dict({block_name})",
        "",
        "    def build_orders(self, state: TradingState) -> list[Order]:",
        "        if not self.params.get(\"ENABLED\", True):",
        "            return []",
        "        touch = self.touch(state)",
        "        if touch is None:",
        "            return []",
        "        best_bid, bid_volume, best_ask, ask_volume = touch",
        "        position = self.current_position(state)",
        "        fair = self.mid_price(best_bid, best_ask)",
        "        fair -= self.params.get(\"INVENTORY_SKEW\", 0.0) * self.inventory_ratio(position) * self.tick_size_value",
        "        orders: list[Order] = []",
        "        take_edge = float(self.params.get(\"TAKE_EDGE\", 1.0))",
        "        if best_ask <= fair - take_edge:",
        "            qty = min(self.take_size(position), self.buy_capacity(position), ask_volume)",
        "            if qty > 0:",
        "                orders.append(Order(self.product, best_ask, qty))",
        "        if best_bid >= fair + take_edge:",
        "            qty = min(self.take_size(position), self.sell_capacity(position), bid_volume)",
        "            if qty > 0:",
        "                orders.append(Order(self.product, best_bid, -qty))",
        "        self.add_passive_quotes(orders, fair, position, best_bid, best_ask)",
        "        return orders",
        "",
    ]


def _stub_class_block(product: ProductSpec, archetype: str) -> list[str]:
    class_name = _product_class_name(product.symbol)
    block_name = _params_block_name(product.symbol)
    capability_comment = ", ".join(_capability_names(product)) or "manual review needed"
    mechanics_comment = ", ".join(product.mechanics) if product.mechanics else "none declared"
    todo = {
        "derivative_stub": "Implement theoretical value, hedge logic, and expiry handling from the competition brief.",
        "spread_stub": "Implement spread fair, hedge ratios, and multi-product execution for the linked sleeve.",
        "participant_stub": "Implement participant tracking and decide whether to follow or fade informed flow.",
    }[archetype]
    return [
        f"class {class_name}(BaseProductTrader):",
        f"    # Archetype: {archetype}",
        f"    # Recommended capabilities: {capability_comment}",
        f"    # Mechanics: {mechanics_comment}",
        f"    # TODO: {todo}",
        "    def default_params(self) -> dict:",
        f"        return dict({block_name})",
        "",
        "    def build_orders(self, state: TradingState) -> list[Order]:",
        "        # Generated as a safe stub because this product family needs deliberate structure.",
        "        return []",
        "",
    ]


def _render_product_class(product: ProductSpec) -> list[str]:
    archetype = _choose_archetype(product)
    if archetype == "anchored_mm":
        return _anchored_class_block(product)
    if archetype == "directional_mm":
        return _directional_class_block(product)
    if archetype == "simple_mm":
        return _simple_mm_class_block(product)
    return _stub_class_block(product, archetype)


def _render_trader(spec: CompetitionSpec) -> str:
    product_setup_lines = []
    product_class_blocks: list[str] = []
    param_blocks = _render_param_blocks(spec)

    for product in spec.products:
        class_name = _product_class_name(product.symbol)
        block_name = _params_block_name(product.symbol)
        product_setup_lines.append(
            f'            "{product.symbol}": {class_name}("{product.symbol}", PRODUCT_LIMITS["{product.symbol}"], PRODUCT_METADATA["{product.symbol}"], {block_name}),'
        )
        product_class_blocks.extend(_render_product_class(product))

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
        "from params import PRODUCT_LIMITS, PRODUCT_METADATA",
        "",
        *param_blocks,
        "class BaseProductTrader:",
        "    def __init__(self, product: str, position_limit: int, metadata: dict, params: dict) -> None:",
        "        self.product = product",
        "        self.position_limit = int(position_limit)",
        "        self.metadata = metadata",
        "        self.params = dict(params)",
        "        self.tick_size_value = float(metadata.get(\"tick_size\", 1.0))",
        "",
        "    def default_params(self) -> dict:",
        "        raise NotImplementedError",
        "",
        "    def current_position(self, state: TradingState) -> int:",
        "        return int(state.position.get(self.product, 0))",
        "",
        "    def order_depth(self, state: TradingState):",
        "        return state.order_depths.get(self.product)",
        "",
        "    def touch(self, state: TradingState):",
        "        depth = self.order_depth(state)",
        "        if depth is None or not depth.buy_orders or not depth.sell_orders:",
        "            return None",
        "        best_bid = max(depth.buy_orders)",
        "        best_ask = min(depth.sell_orders)",
        "        return int(best_bid), int(depth.buy_orders[best_bid]), int(best_ask), abs(int(depth.sell_orders[best_ask]))",
        "",
        "    @staticmethod",
        "    def clamp(value: float, low: float, high: float) -> float:",
        "        return max(low, min(high, value))",
        "",
        "    def mid_price(self, best_bid: int, best_ask: int) -> float:",
        "        return (best_bid + best_ask) / 2.0",
        "",
        "    def microprice(self, best_bid: int, bid_volume: int, best_ask: int, ask_volume: int) -> float:",
        "        total = bid_volume + ask_volume",
        "        if total <= 0:",
        "            return self.mid_price(best_bid, best_ask)",
        "        return (best_bid * ask_volume + best_ask * bid_volume) / total",
        "",
        "    def top_imbalance(self, bid_volume: int, ask_volume: int) -> float:",
        "        total = bid_volume + ask_volume",
        "        if total <= 0:",
        "            return 0.0",
        "        return (bid_volume - ask_volume) / total",
        "",
        "    def inventory_ratio(self, position: int) -> float:",
        "        return position / max(1, self.position_limit)",
        "",
        "    def buy_capacity(self, position: int) -> int:",
        "        return max(0, self.position_limit - position)",
        "",
        "    def sell_capacity(self, position: int) -> int:",
        "        return max(0, self.position_limit + position)",
        "",
        "    def passive_size(self, position: int, side: str) -> int:",
        "        base = max(1, int(self.params.get(\"MAX_PASSIVE_SIZE\", 1)))",
        "        ratio = self.inventory_ratio(position)",
        "        scale = 1.0 - ratio if side == \"buy\" else 1.0 + ratio",
        "        scale = self.clamp(scale, 0.25, 1.75)",
        "        return max(1, int(round(base * scale)))",
        "",
        "    def take_size(self, position: int) -> int:",
        "        del position",
        "        return max(1, int(self.params.get(\"MAX_TAKE_SIZE\", 1)))",
        "",
        "    def snap_price(self, raw_price: float) -> int:",
        "        if self.tick_size_value <= 0:",
        "            return int(round(raw_price))",
        "        return int(round(round(raw_price / self.tick_size_value) * self.tick_size_value))",
        "",
        "    def add_passive_quotes(self, orders: list[Order], fair: float, position: int, best_bid: int, best_ask: int) -> None:",
        "        quote_edge = float(self.params.get(\"QUOTE_EDGE\", 2.0))",
        "        buy_quote = self.snap_price(fair - quote_edge)",
        "        sell_quote = self.snap_price(fair + quote_edge)",
        "        if buy_quote < best_ask:",
        "            buy_qty = min(self.passive_size(position, \"buy\"), self.buy_capacity(position))",
        "            if buy_qty > 0:",
        "                orders.append(Order(self.product, buy_quote, buy_qty))",
        "        if sell_quote > best_bid:",
        "            sell_qty = min(self.passive_size(position, \"sell\"), self.sell_capacity(position))",
        "            if sell_qty > 0:",
        "                orders.append(Order(self.product, sell_quote, -sell_qty))",
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
        "        trader_data = state.traderData if hasattr(state, \"traderData\") else \"\"",
        "        return orders, 0, trader_data",
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
        "- `params.py`: product limits and metadata",
        "- `trader.py`: runnable multi-product baseline with capability-aware sleeves",
        "- `experiments/`: deterministic, Monte Carlo, optimization, and official-analysis templates",
        "- `research/`: probe suggestions and research notes",
        "- `notes.md`: room for round-specific discoveries and handoff notes",
        "",
        "## Working Rule",
        "",
        "- start with the generated baseline trader",
        "- validate with deterministic replay",
        "- validate with Monte Carlo robustness",
        "- use experiment templates before inventing new workflow files",
        "- switch into research mode only when local and official behavior diverge materially",
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
        "- confirm which generated archetypes are acceptable and which need manual redesign",
        "- run deterministic replay and capture baseline scores before touching optimization configs",
        "- decide whether the next step is development mode or research mode",
        "",
        "Products:",
    ]
    for product in spec.products:
        lines.append(f"- {product.symbol}: {product.notes or 'no extra notes yet'}")
    lines.append("")
    return "\n".join(lines)


def _render_experiments_readme(project_name: str, spec: CompetitionSpec) -> str:
    lines = [
        "# Experiments",
        "",
        f"Generated experiment assets for `{project_name}`.",
        "",
        "## Suggested Order",
        "",
        "1. Run deterministic replay on `trader.py` for the target days.",
        "2. Update the CMA-ES template baselines with the observed deterministic totals.",
        "3. Run Monte Carlo on the generated trader before making structural changes.",
        "4. After an official submission, run the official diagnostics against the saved `.log` / `.json` files.",
        "",
        "## Core Commands",
        "",
        "```bash",
        "python3 -m trader_factory.cli deterministic ./trader.py --day -1",
        "python3 -m trader_factory.cli deterministic ./trader.py --day -2",
        "python3 -m trader_factory.cli monte-carlo ./trader.py --quick",
        "python3 -m trader_factory.cli official-trade-quality /absolute/path/to/run.log",
        "```",
        "",
        "## Product Archetypes",
        "",
    ]
    for product in spec.products:
        lines.append(
            f"- `{product.symbol}`: archetype `{_choose_archetype(product)}` with capabilities {', '.join(_capability_names(product)) or 'manual review needed'}"
        )
    lines.append("")
    return "\n".join(lines)


def _cmaes_parameters_for_archetype(archetype: str) -> list[dict[str, Any]]:
    if archetype == "anchored_mm":
        return [
            {"name": "TAKE_EDGE", "lower": 0.5, "upper": 2.0},
            {"name": "QUOTE_EDGE", "lower": 1.0, "upper": 3.5},
            {"name": "INVENTORY_SKEW", "lower": 0.1, "upper": 1.5},
        ]
    if archetype == "directional_mm":
        return [
            {"name": "TAKE_EDGE", "lower": 0.4, "upper": 1.6},
            {"name": "QUOTE_EDGE", "lower": 0.8, "upper": 3.0},
            {"name": "IMBALANCE_SHIFT", "lower": 0.1, "upper": 2.0},
            {"name": "MICROPRICE_WEIGHT", "lower": 0.0, "upper": 1.5},
            {"name": "REVERSION_WEIGHT", "lower": 0.0, "upper": 1.0},
            {"name": "INVENTORY_SKEW", "lower": 0.0, "upper": 1.2},
        ]
    if archetype == "simple_mm":
        return [
            {"name": "TAKE_EDGE", "lower": 0.5, "upper": 2.0},
            {"name": "QUOTE_EDGE", "lower": 1.0, "upper": 4.0},
            {"name": "INVENTORY_SKEW", "lower": 0.0, "upper": 1.2},
        ]
    return []


def _render_cmaes_template(product: ProductSpec) -> str | None:
    archetype = _choose_archetype(product)
    parameters = _cmaes_parameters_for_archetype(archetype)
    if not parameters:
        return None
    payload = {
        "name": f"{product.symbol} Baseline Template",
        "source_bot": "../trader.py",
        "default_dict_block": _params_block_name(product.symbol),
        "baselines": {"-2": 0.0, "-1": 0.0},
        "search": {
            "max_iter": 5,
            "population": 6,
            "parents": 3,
            "sigma0": 0.08,
            "seed": 52,
            "timeout_seconds": 120,
        },
        "penalties": {"regression": 2.0, "imbalance": 0.4, "drift": 40.0},
        "output_prefix": f"{product.symbol.lower()}_baseline_template",
        "parameters": parameters,
    }
    return json.dumps(payload, indent=2) + "\n"


def _render_research_readme(spec: CompetitionSpec) -> str:
    lines = [
        "# Research",
        "",
        "Use this directory when development mode is not enough.",
        "",
        "Switch into research mode when:",
        "",
        "- local replay and official submissions diverge materially",
        "- a candidate feature appears dormant",
        "- passive or aggressive execution behavior is unclear",
        "",
        "Probe targets from this spec:",
    ]
    flagged = False
    for product in spec.products:
        capabilities = set(_capability_names(product))
        if "execution_probe_suite" in capabilities or "unknown_execution" in product.mechanics:
            flagged = True
            lines.extend(
                [
                    f"- `{product.symbol}`",
                    f"  - start with `boundary` for dormant-vs-live questions",
                    f"  - use `aggressive_markout` for taker-context questions",
                    f"  - use `passive_ladder` if passive fill assumptions are suspect",
                ]
            )
    if not flagged:
        lines.append("- No products were explicitly flagged for execution research from the current spec.")
    lines.append("")
    return "\n".join(lines)


def _render_probe_targets(spec: CompetitionSpec) -> str:
    lines = [
        "# Probe Targets",
        "",
        "Use this file to decide when a generated project should switch from development mode to research mode.",
        "",
    ]
    for product in spec.products:
        capabilities = set(_capability_names(product))
        lines.append(f"## {product.symbol}")
        lines.append("")
        if "execution_probe_suite" in capabilities or "unknown_execution" in product.mechanics:
            lines.extend(
                [
                    "- Suggested first probes:",
                    f"  - `python3 -m trader_factory.cli probe-scaffold boundary ./trader.py --product {product.symbol}`",
                    f"  - `python3 -m trader_factory.cli probe-scaffold aggressive_markout ./trader.py --product {product.symbol} --context range_buy`",
                    f"  - `python3 -m trader_factory.cli probe-scaffold passive_ladder ./trader.py --product {product.symbol}`",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "- No immediate probe recommendation from the current mechanics.",
                    "- Stay in development mode unless official behavior disagrees with local replay.",
                    "",
                ]
            )
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
    experiments_dir = workspace / "experiments"
    research_dir = workspace / "research"

    experiments_dir.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)

    readme_path.write_text(_render_readme(spec, name) + "\n")
    spec_copy_path.write_text(json.dumps(json.loads(spec_file.read_text()), indent=2) + "\n")
    plan_path.write_text(render_markdown_plan(spec))
    trader_path.write_text(_render_trader(spec))
    params_path.write_text(_render_params(spec))
    notes_path.write_text(_render_notes(spec))
    (experiments_dir / "README.md").write_text(_render_experiments_readme(name, spec) + "\n")
    (research_dir / "README.md").write_text(_render_research_readme(spec) + "\n")
    (research_dir / "probe_targets.md").write_text(_render_probe_targets(spec) + "\n")

    for product in spec.products:
        template = _render_cmaes_template(product)
        if template is not None:
            (experiments_dir / f"cmaes_template_{product.symbol.lower()}.json").write_text(template)

    return TraderProjectResult(
        project_name=name,
        output_dir=workspace,
        readme_path=readme_path,
        spec_copy_path=spec_copy_path,
        plan_path=plan_path,
        trader_path=trader_path,
        params_path=params_path,
        notes_path=notes_path,
        experiments_dir=experiments_dir,
        research_dir=research_dir,
    )
