from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trader_factory.core.mapping import ProductInterpretation, interpret_competition, interpret_product
from trader_factory.core.specs import CompetitionSpec, ProductSpec
from trader_factory.core.validation import render_validation_markdown, validate_competition_spec
from trader_factory.generation.bootstrap import render_markdown_plan
from trader_factory.strategies import ArchetypeBlueprint, BlueprintMethod, get_archetype_blueprint


@dataclass(slots=True)
class TraderProjectResult:
    project_name: str
    output_dir: Path
    readme_path: Path
    spec_copy_path: Path
    spec_validation_path: Path
    spec_validation_json_path: Path
    plan_path: Path
    trader_path: Path
    params_path: Path
    notes_path: Path
    round_start_checklist_path: Path
    experiments_dir: Path
    research_dir: Path
    structural_design_brief_path: Path
    gate_policy_template_path: Path


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


def _product_interpretation(product: ProductSpec, spec: CompetitionSpec | None = None) -> ProductInterpretation:
    return interpret_product(product, spec)


def _choose_archetype(product: ProductSpec, spec: CompetitionSpec | None = None) -> str:
    return _product_interpretation(product, spec).preferred_archetype


def _archetype_blueprint(archetype: str) -> ArchetypeBlueprint | None:
    return get_archetype_blueprint(archetype)


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
    if archetype == "spread_mm":
        return [
            ("ENABLED", True),
            ("SPREAD_THRESHOLD", 1.0),
            ("QUOTE_EDGE", 2.0),
            ("MAX_PASSIVE_SIZE", passive_size),
            ("MAX_TAKE_SIZE", take_size),
            ("REFERENCE_WEIGHT", 0.75),
            ("DEFAULT_HEDGE_RATIO", 1.0),
            ("SPREAD_OFFSET", 0.0),
            ("ALLOW_OWN_MID_FALLBACK", True),
            ("INVENTORY_SKEW", 0.5),
        ]
    if archetype == "basket_mm":
        return [
            ("ENABLED", True),
            ("BASKET_THRESHOLD", 1.0),
            ("QUOTE_EDGE", 2.0),
            ("MAX_PASSIVE_SIZE", passive_size),
            ("MAX_TAKE_SIZE", take_size),
            ("REFERENCE_WEIGHT", 0.85),
            ("PREMIUM_OFFSET", 0.0),
            ("ALLOW_OWN_MID_FALLBACK", True),
            ("INVENTORY_SKEW", 0.5),
        ]
    if archetype == "derivative_mm":
        return [
            ("ENABLED", True),
            ("TAKE_EDGE", 1.0),
            ("QUOTE_EDGE", 2.5),
            ("MAX_PASSIVE_SIZE", passive_size),
            ("MAX_TAKE_SIZE", take_size),
            ("THEORETICAL_WEIGHT", 1.0),
            ("VOLATILITY_OVERRIDE", None),
            ("INVENTORY_SKEW", 0.4),
        ]
    if archetype == "conversion_mm":
        return [
            ("ENABLED", True),
            ("ARB_THRESHOLD", 1.0),
            ("QUOTE_EDGE", 2.0),
            ("MAX_PASSIVE_SIZE", passive_size),
            ("MAX_TAKE_SIZE", take_size),
            ("REFERENCE_WEIGHT", 0.75),
            ("EXTRA_CONVERSION_FEE", 0.0),
            ("ALLOW_POSITION_FLATTEN_CONVERSIONS", False),
            ("INVENTORY_SKEW", 0.4),
        ]
    if archetype == "participant_mm":
        participant_rule = product.participant_rule
        return [
            ("ENABLED", True),
            ("TAKE_EDGE", 1.0),
            ("QUOTE_EDGE", 2.0),
            ("MAX_PASSIVE_SIZE", passive_size),
            ("MAX_TAKE_SIZE", take_size),
            ("SIGNAL_THRESHOLD", 0.25),
            ("SIGNAL_WEIGHT", 2.0),
            ("MIN_MATCHED_VOLUME", 1),
            ("FOLLOW_MODE", (participant_rule.follow_mode if participant_rule is not None and participant_rule.follow_mode else "follow")),
            ("TRACKED_PARTICIPANTS", [] if participant_rule is None else list(participant_rule.tracked_participants)),
            ("PARTICIPANT_WEIGHTS", {} if participant_rule is None else dict(participant_rule.participant_weights)),
            ("INVENTORY_SKEW", 0.5),
        ]
    if archetype == "signal_mm":
        return [
            ("ENABLED", True),
            ("TAKE_EDGE", 1.0),
            ("QUOTE_EDGE", 2.0),
            ("MAX_PASSIVE_SIZE", passive_size),
            ("MAX_TAKE_SIZE", take_size),
            ("SIGNAL_WEIGHT", 1.5),
            ("SIGNAL_SCALE", 1.0),
            ("SIGNAL_BASELINE", 0.0),
            ("MAX_SIGNAL_ABS", 3.0),
            ("SIGNAL_THRESHOLD", 0.15),
            ("INVENTORY_SKEW", 0.5),
        ]
    blueprint = _archetype_blueprint(archetype)
    if blueprint is not None:
        return list(blueprint.default_params)
    return [
        ("ENABLED", True),
        ("TODO_NOTE", f"Implement a {archetype} sleeve for {product.symbol} based on the round brief."),
    ]


def _render_params(spec: CompetitionSpec) -> str:
    interpretations = interpret_competition(spec)
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
        interpretation = interpretations[product.symbol]
        capabilities = [cap.name for cap in interpretation.recommended_capabilities]
        archetype = interpretation.preferred_archetype
        observation_channels = [channel.to_dict() for channel in product.observation_channels]
        basket_definition = None if product.basket_definition is None else product.basket_definition.to_dict()
        participant_rule = None if product.participant_rule is None else product.participant_rule.to_dict()
        signal_rule = None if product.signal_rule is None else product.signal_rule.to_dict()
        derivative_contract = None if product.derivative_contract is None else product.derivative_contract.to_dict()
        conversion_rule = None if product.conversion_rule is None else product.conversion_rule.to_dict()
        auction_rule = None if product.auction_rule is None else product.auction_rule.to_dict()
        relationship_details = []
        for relationship in spec.relationships_for(product.symbol):
            relationship_details.append(
                {
                    "counterpart": relationship.counterpart(product.symbol),
                    "relationship": relationship.relationship,
                    "hedge_ratio": relationship.hedge_ratio,
                    "description": relationship.description,
                    "tags": relationship.tags,
                }
            )
        lines += [
            f'    "{product.symbol}": {{',
            f'        "tick_size": {product.tick_size},',
            f'        "price_regime": "{product.price_regime}",',
            f'        "execution_style": "{product.execution_style}",',
            f'        "mechanics": {json.dumps(interpretation.recognized_mechanics)},',
            f'        "unknown_mechanics": {json.dumps(interpretation.unknown_mechanics)},',
            f'        "observations": {json.dumps(product.observations)},',
            f'        "observation_channels": {json.dumps(observation_channels, sort_keys=True)},',
            f'        "basket_definition": {json.dumps(basket_definition, sort_keys=True)},',
            f'        "participant_rule": {json.dumps(participant_rule, sort_keys=True)},',
            f'        "signal_rule": {json.dumps(signal_rule, sort_keys=True)},',
            f'        "derivative_contract": {json.dumps(derivative_contract, sort_keys=True)},',
            f'        "conversion_rule": {json.dumps(conversion_rule, sort_keys=True)},',
            f'        "auction_rule": {json.dumps(auction_rule, sort_keys=True)},',
            f'        "related_products": {json.dumps(interpretation.related_products)},',
            f'        "relationship_details": {json.dumps(relationship_details, sort_keys=True)},',
            f'        "special_rules": {json.dumps(interpretation.special_rules)},',
            f'        "open_questions": {json.dumps(interpretation.open_questions)},',
            f'        "custom_fields": {json.dumps(product.custom_fields, sort_keys=True)},',
            f'        "recommended_capabilities": {json.dumps(capabilities)},',
            f'        "generated_archetype": "{archetype}",',
            f'        "fallback_mode": "{interpretation.fallback_mode}",',
            f'        "research_triggers": {json.dumps(interpretation.research_triggers)},',
            f'        "intake_gaps": {json.dumps(interpretation.intake_gaps)},',
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
        for key, value in _default_param_items(product, _choose_archetype(product, spec)):
            blocks.append(f'    "{key}": {_python_literal(value)},')
        blocks.append("}")
        blocks.append("")
    return blocks


def _render_blueprint_method(method: BlueprintMethod) -> list[str]:
    lines = [f"    {method.signature}"]
    if method.summary:
        lines.append(f"        # {method.summary}")
    if method.body_lines:
        lines.extend(f"        {line}" for line in method.body_lines)
    else:
        lines.append("        pass")
    lines.append("")
    return lines


def _render_blueprint_comments(blueprint: ArchetypeBlueprint | None) -> list[str]:
    if blueprint is None:
        return []
    lines = [f"    # Blueprint: {blueprint.summary}"]
    if blueprint.required_inputs:
        lines.append(f"    # Required inputs: {', '.join(blueprint.required_inputs)}")
    if blueprint.custom_field_examples:
        lines.append(f"    # Useful custom_fields: {', '.join(blueprint.custom_field_examples)}")
    return lines


def _anchored_class_block(product: ProductSpec, spec: CompetitionSpec) -> list[str]:
    class_name = _product_class_name(product.symbol)
    block_name = _params_block_name(product.symbol)
    interpretation = _product_interpretation(product, spec)
    capability_comment = ", ".join(cap.name for cap in interpretation.recommended_capabilities) or "manual review needed"
    mechanics_comment = ", ".join(interpretation.recognized_mechanics) if interpretation.recognized_mechanics else "none declared"
    unknown_comment = ", ".join(interpretation.unknown_mechanics) if interpretation.unknown_mechanics else "none"
    return [
        f"class {class_name}(BaseProductTrader):",
        f"    # Archetype: anchored_mm",
        f"    # Recommended capabilities: {capability_comment}",
        f"    # Mechanics: {mechanics_comment}",
        f"    # Unknown mechanics: {unknown_comment}",
        f"    # Fallback mode: {interpretation.fallback_mode}",
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


def _directional_class_block(product: ProductSpec, spec: CompetitionSpec) -> list[str]:
    class_name = _product_class_name(product.symbol)
    block_name = _params_block_name(product.symbol)
    interpretation = _product_interpretation(product, spec)
    capability_comment = ", ".join(cap.name for cap in interpretation.recommended_capabilities) or "manual review needed"
    mechanics_comment = ", ".join(interpretation.recognized_mechanics) if interpretation.recognized_mechanics else "none declared"
    unknown_comment = ", ".join(interpretation.unknown_mechanics) if interpretation.unknown_mechanics else "none"
    return [
        f"class {class_name}(BaseProductTrader):",
        f"    # Archetype: directional_mm",
        f"    # Recommended capabilities: {capability_comment}",
        f"    # Mechanics: {mechanics_comment}",
        f"    # Unknown mechanics: {unknown_comment}",
        f"    # Fallback mode: {interpretation.fallback_mode}",
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


def _simple_mm_class_block(product: ProductSpec, spec: CompetitionSpec) -> list[str]:
    class_name = _product_class_name(product.symbol)
    block_name = _params_block_name(product.symbol)
    interpretation = _product_interpretation(product, spec)
    capability_comment = ", ".join(cap.name for cap in interpretation.recommended_capabilities) or "manual review needed"
    mechanics_comment = ", ".join(interpretation.recognized_mechanics) if interpretation.recognized_mechanics else "none declared"
    unknown_comment = ", ".join(interpretation.unknown_mechanics) if interpretation.unknown_mechanics else "none"
    return [
        f"class {class_name}(BaseProductTrader):",
        f"    # Archetype: simple_mm",
        f"    # Recommended capabilities: {capability_comment}",
        f"    # Mechanics: {mechanics_comment}",
        f"    # Unknown mechanics: {unknown_comment}",
        f"    # Fallback mode: {interpretation.fallback_mode}",
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


def _spread_mm_class_block(product: ProductSpec, spec: CompetitionSpec) -> list[str]:
    class_name = _product_class_name(product.symbol)
    block_name = _params_block_name(product.symbol)
    interpretation = _product_interpretation(product, spec)
    capability_comment = ", ".join(cap.name for cap in interpretation.recommended_capabilities) or "manual review needed"
    mechanics_comment = ", ".join(interpretation.recognized_mechanics) if interpretation.recognized_mechanics else "none declared"
    unknown_comment = ", ".join(interpretation.unknown_mechanics) if interpretation.unknown_mechanics else "none"
    return [
        f"class {class_name}(BaseProductTrader):",
        f"    # Archetype: spread_mm",
        f"    # Recommended capabilities: {capability_comment}",
        f"    # Mechanics: {mechanics_comment}",
        f"    # Unknown mechanics: {unknown_comment}",
        f"    # Fallback mode: {interpretation.fallback_mode}",
        "    def default_params(self) -> dict:",
        f"        return dict({block_name})",
        "",
        "    def reference_fair(self, state: TradingState, own_mid: float) -> float | None:",
        "        related_symbols = list(self.metadata.get(\"related_products\", []))",
        "        related_mid_prices = {symbol: self.mid_for_symbol(state, symbol) for symbol in related_symbols}",
        "        fair = linked_reference_fair(",
        "            own_mid=own_mid,",
        "            related_mid_prices=related_mid_prices,",
        "            related_symbols=related_symbols,",
        "            relationship_details=self.metadata.get(\"relationship_details\", []),",
        "            default_hedge_ratio=float(self.params.get(\"DEFAULT_HEDGE_RATIO\", 1.0)),",
        "            reference_weight=float(self.params.get(\"REFERENCE_WEIGHT\", 0.75)),",
        "            spread_offset=float(self.params.get(\"SPREAD_OFFSET\", 0.0)),",
        "        )",
        "        if fair is None and self.params.get(\"ALLOW_OWN_MID_FALLBACK\", True):",
        "            return own_mid",
        "        return fair",
        "",
        "    def build_orders(self, state: TradingState) -> list[Order]:",
        "        if not self.params.get(\"ENABLED\", True):",
        "            return []",
        "        touch = self.touch(state)",
        "        if touch is None:",
        "            return []",
        "        best_bid, bid_volume, best_ask, ask_volume = touch",
        "        position = self.current_position(state)",
        "        own_mid = self.mid_price(best_bid, best_ask)",
        "        fair = self.reference_fair(state, own_mid)",
        "        if fair is None:",
        "            return []",
        "        fair -= self.params.get(\"INVENTORY_SKEW\", 0.0) * self.inventory_ratio(position) * self.tick_size_value",
        "        orders: list[Order] = []",
        "        spread_threshold = float(self.params.get(\"SPREAD_THRESHOLD\", 1.0))",
        "        if best_ask <= fair - spread_threshold:",
        "            qty = min(self.take_size(position), self.buy_capacity(position), ask_volume)",
        "            if qty > 0:",
        "                orders.append(Order(self.product, best_ask, qty))",
        "        if best_bid >= fair + spread_threshold:",
        "            qty = min(self.take_size(position), self.sell_capacity(position), bid_volume)",
        "            if qty > 0:",
        "                orders.append(Order(self.product, best_bid, -qty))",
        "        self.add_passive_quotes(orders, fair, position, best_bid, best_ask)",
        "        return orders",
        "",
    ]


def _basket_mm_class_block(product: ProductSpec, spec: CompetitionSpec) -> list[str]:
    class_name = _product_class_name(product.symbol)
    block_name = _params_block_name(product.symbol)
    interpretation = _product_interpretation(product, spec)
    capability_comment = ", ".join(cap.name for cap in interpretation.recommended_capabilities) or "manual review needed"
    mechanics_comment = ", ".join(interpretation.recognized_mechanics) if interpretation.recognized_mechanics else "none declared"
    unknown_comment = ", ".join(interpretation.unknown_mechanics) if interpretation.unknown_mechanics else "none"
    return [
        f"class {class_name}(BaseProductTrader):",
        f"    # Archetype: basket_mm",
        f"    # Recommended capabilities: {capability_comment}",
        f"    # Mechanics: {mechanics_comment}",
        f"    # Unknown mechanics: {unknown_comment}",
        f"    # Fallback mode: {interpretation.fallback_mode}",
        "    def default_params(self) -> dict:",
        f"        return dict({block_name})",
        "",
        "    def basket_reference(self, state: TradingState, own_mid: float) -> float | None:",
        "        basket_definition = self.metadata.get(\"basket_definition\") or {}",
        "        custom_fields = self.metadata.get(\"custom_fields\", {})",
        "        component_specs = basket_definition.get(\"components\") or custom_fields.get(\"components\", [])",
        "        component_mid_prices = {",
        "            str(component.get(\"symbol\", component.get(\"counterpart\", \"\"))).strip(): self.mid_for_symbol(state, str(component.get(\"symbol\", component.get(\"counterpart\", \"\"))).strip())",
        "            for component in component_specs",
        "            if str(component.get(\"symbol\", component.get(\"counterpart\", \"\"))).strip()",
        "        }",
        "        basket_divisor = self.parse_float(basket_definition.get(\"divisor\"))",
        "        if basket_divisor is None:",
        "            basket_divisor = self.parse_float(custom_fields.get(\"basket_divisor\"))",
        "        if basket_divisor is None:",
        "            basket_divisor = 1.0",
        "        fair_offset = self.parse_float(basket_definition.get(\"fair_offset\"))",
        "        if fair_offset is None:",
        "            fair_offset = self.parse_float(custom_fields.get(\"fair_offset\"))",
        "        if fair_offset is None:",
        "            fair_offset = 0.0",
        "        fair = basket_reference_fair(",
        "            component_mid_prices=component_mid_prices,",
        "            component_specs=component_specs,",
        "            basket_divisor=basket_divisor,",
        "            fair_offset=float(self.params.get(\"PREMIUM_OFFSET\", 0.0)) + fair_offset,",
        "        )",
        "        if fair is None and self.params.get(\"ALLOW_OWN_MID_FALLBACK\", True):",
        "            return own_mid",
        "        if fair is None:",
        "            return None",
        "        reference_weight = float(self.params.get(\"REFERENCE_WEIGHT\", 0.85))",
        "        reference_weight = self.clamp(reference_weight, 0.0, 1.0)",
        "        return reference_weight * fair + (1.0 - reference_weight) * own_mid",
        "",
        "    def build_orders(self, state: TradingState) -> list[Order]:",
        "        if not self.params.get(\"ENABLED\", True):",
        "            return []",
        "        touch = self.touch(state)",
        "        if touch is None:",
        "            return []",
        "        best_bid, bid_volume, best_ask, ask_volume = touch",
        "        position = self.current_position(state)",
        "        own_mid = self.mid_price(best_bid, best_ask)",
        "        fair = self.basket_reference(state, own_mid)",
        "        if fair is None:",
        "            return []",
        "        fair -= self.params.get(\"INVENTORY_SKEW\", 0.0) * self.inventory_ratio(position) * self.tick_size_value",
        "        orders: list[Order] = []",
        "        basket_threshold = float(self.params.get(\"BASKET_THRESHOLD\", 1.0))",
        "        if best_ask <= fair - basket_threshold:",
        "            qty = min(self.take_size(position), self.buy_capacity(position), ask_volume)",
        "            if qty > 0:",
        "                orders.append(Order(self.product, best_ask, qty))",
        "        if best_bid >= fair + basket_threshold:",
        "            qty = min(self.take_size(position), self.sell_capacity(position), bid_volume)",
        "            if qty > 0:",
        "                orders.append(Order(self.product, best_bid, -qty))",
        "        self.add_passive_quotes(orders, fair, position, best_bid, best_ask)",
        "        return orders",
        "",
    ]


def _derivative_mm_class_block(product: ProductSpec, spec: CompetitionSpec) -> list[str]:
    class_name = _product_class_name(product.symbol)
    block_name = _params_block_name(product.symbol)
    interpretation = _product_interpretation(product, spec)
    capability_comment = ", ".join(cap.name for cap in interpretation.recommended_capabilities) or "manual review needed"
    mechanics_comment = ", ".join(interpretation.recognized_mechanics) if interpretation.recognized_mechanics else "none declared"
    unknown_comment = ", ".join(interpretation.unknown_mechanics) if interpretation.unknown_mechanics else "none"
    return [
        f"class {class_name}(BaseProductTrader):",
        f"    # Archetype: derivative_mm",
        f"    # Recommended capabilities: {capability_comment}",
        f"    # Mechanics: {mechanics_comment}",
        f"    # Unknown mechanics: {unknown_comment}",
        f"    # Fallback mode: {interpretation.fallback_mode}",
        "    def default_params(self) -> dict:",
        f"        return dict({block_name})",
        "",
        "    def derivative_reference(self, state: TradingState):",
        "        derivative_contract = self.metadata.get(\"derivative_contract\") or {}",
        "        custom_fields = self.metadata.get(\"custom_fields\", {})",
        "        underlying = str(derivative_contract.get(\"underlying\") or custom_fields.get(\"underlying\") or \"\").strip()",
        "        if not underlying:",
        "            return None",
        "        spot = self.mid_for_symbol(state, underlying)",
        "        if spot is None:",
        "            return None",
        "        strike = self.parse_float(derivative_contract.get(\"strike\"))",
        "        if strike is None:",
        "            strike = self.parse_float(custom_fields.get(\"strike\"))",
        "        option_kind = str(derivative_contract.get(\"option_kind\") or custom_fields.get(\"option_kind\", custom_fields.get(\"option_type\", \"\")) or \"\").strip().lower()",
        "        volatility = self.parse_float(self.params.get(\"VOLATILITY_OVERRIDE\"))",
        "        if volatility is None:",
        "            volatility = self.parse_float(derivative_contract.get(\"volatility\"))",
        "        if volatility is None:",
        "            volatility = self.parse_float(custom_fields.get(\"volatility\"))",
        "        if volatility is None:",
        "            volatility = self.parse_float(custom_fields.get(\"implied_volatility\"))",
        "        if volatility is None:",
        "            volatility_percent = self.parse_float(custom_fields.get(\"volatility_percent\"))",
        "            if volatility_percent is not None:",
        "                volatility = volatility_percent / 100.0",
        "        time_to_expiry = self.parse_float(derivative_contract.get(\"time_to_expiry_years\"))",
        "        if time_to_expiry is None:",
        "            time_to_expiry = self.parse_float(custom_fields.get(\"time_to_expiry_years\"))",
        "        if time_to_expiry is None:",
        "            time_to_expiry = self.parse_float(custom_fields.get(\"expiry_years\"))",
        "        if time_to_expiry is None:",
        "            expiry_days = self.parse_float(custom_fields.get(\"days_to_expiry\"))",
        "            if expiry_days is None:",
        "                expiry_days = self.parse_float(custom_fields.get(\"expiry_days\"))",
        "            if expiry_days is None:",
        "                expiry_days = self.parse_float(custom_fields.get(\"time_to_expiry_days\"))",
        "            if expiry_days is not None:",
        "                time_to_expiry = max(0.0, expiry_days) / 365.0",
        "        if strike is None or volatility is None or time_to_expiry is None or option_kind not in {\"call\", \"put\"}:",
        "            return None",
        "        risk_free_rate = self.parse_float(derivative_contract.get(\"risk_free_rate\"))",
        "        if risk_free_rate is None:",
        "            risk_free_rate = self.parse_float(custom_fields.get(\"risk_free_rate\"))",
        "        if risk_free_rate is None:",
        "            risk_free_rate = 0.0",
        "        carry_rate = self.parse_float(derivative_contract.get(\"carry_rate\"))",
        "        if carry_rate is None:",
        "            carry_rate = self.parse_float(custom_fields.get(\"dividend_yield\"))",
        "        if carry_rate is None:",
        "            carry_rate = self.parse_float(custom_fields.get(\"carry_rate\"))",
        "        if carry_rate is None:",
        "            carry_rate = 0.0",
        "        return black_scholes_option_reference(",
        "            spot=spot,",
        "            strike=strike,",
        "            time_to_expiry_years=time_to_expiry,",
        "            volatility=volatility,",
        "            option_kind=option_kind,",
        "            risk_free_rate=risk_free_rate,",
        "            carry_rate=carry_rate,",
        "        )",
        "",
        "    def build_orders(self, state: TradingState) -> list[Order]:",
        "        if not self.params.get(\"ENABLED\", True):",
        "            return []",
        "        touch = self.touch(state)",
        "        reference = self.derivative_reference(state)",
        "        if touch is None or reference is None:",
        "            return []",
        "        best_bid, bid_volume, best_ask, ask_volume = touch",
        "        position = self.current_position(state)",
        "        local_mid = self.mid_price(best_bid, best_ask)",
        "        theoretical_weight = float(self.params.get(\"THEORETICAL_WEIGHT\", 1.0))",
        "        theoretical_weight = self.clamp(theoretical_weight, 0.0, 1.0)",
        "        fair = theoretical_weight * reference.fair_value + (1.0 - theoretical_weight) * local_mid",
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


def _conversion_mm_class_block(product: ProductSpec, spec: CompetitionSpec) -> list[str]:
    class_name = _product_class_name(product.symbol)
    block_name = _params_block_name(product.symbol)
    interpretation = _product_interpretation(product, spec)
    capability_comment = ", ".join(cap.name for cap in interpretation.recommended_capabilities) or "manual review needed"
    mechanics_comment = ", ".join(interpretation.recognized_mechanics) if interpretation.recognized_mechanics else "none declared"
    unknown_comment = ", ".join(interpretation.unknown_mechanics) if interpretation.unknown_mechanics else "none"
    return [
        f"class {class_name}(BaseProductTrader):",
        f"    # Archetype: conversion_mm",
        f"    # Recommended capabilities: {capability_comment}",
        f"    # Mechanics: {mechanics_comment}",
        f"    # Unknown mechanics: {unknown_comment}",
        f"    # Fallback mode: {interpretation.fallback_mode}",
        "    def default_params(self) -> dict:",
        f"        return dict({block_name})",
        "",
        "    def conversion_reference(self, state: TradingState):",
        "        observation = self.conversion_observation(state)",
        "        if observation is None:",
        "            return None",
        "        conversion_rule = self.metadata.get(\"conversion_rule\") or {}",
        "        extra_fee = float(self.params.get(\"EXTRA_CONVERSION_FEE\", 0.0))",
        "        rule_fee = self.parse_float(conversion_rule.get(\"fee\"))",
        "        if rule_fee is None:",
        "            rule_fee = self.parse_float(self.metadata.get(\"custom_fields\", {}).get(\"conversion_fee\"))",
        "        if rule_fee is not None:",
        "            extra_fee += rule_fee",
        "        return conversion_reference_prices(",
        "            bid_price=observation.bidPrice,",
        "            ask_price=observation.askPrice,",
        "            transport_fees=observation.transportFees,",
        "            export_tariff=observation.exportTariff,",
        "            import_tariff=observation.importTariff,",
        "            extra_fee=extra_fee,",
        "        )",
        "",
        "    def build_orders(self, state: TradingState) -> list[Order]:",
        "        if not self.params.get(\"ENABLED\", True):",
        "            return []",
        "        touch = self.touch(state)",
        "        reference = self.conversion_reference(state)",
        "        if touch is None or reference is None:",
        "            return []",
        "        best_bid, bid_volume, best_ask, ask_volume = touch",
        "        position = self.current_position(state)",
        "        local_mid = self.mid_price(best_bid, best_ask)",
        "        fair = float(self.params.get(\"REFERENCE_WEIGHT\", 0.75)) * reference.fair_value + (1.0 - float(self.params.get(\"REFERENCE_WEIGHT\", 0.75))) * local_mid",
        "        fair -= self.params.get(\"INVENTORY_SKEW\", 0.0) * self.inventory_ratio(position) * self.tick_size_value",
        "        buy_export_edge, import_sell_edge = conversion_edges(",
        "            local_best_bid=best_bid,",
        "            local_best_ask=best_ask,",
        "            reference=reference,",
        "        )",
        "        threshold = float(self.params.get(\"ARB_THRESHOLD\", 1.0))",
        "        orders: list[Order] = []",
        "        if buy_export_edge >= threshold:",
        "            qty = min(self.take_size(position), self.buy_capacity(position), ask_volume)",
        "            if qty > 0:",
        "                orders.append(Order(self.product, best_ask, qty))",
        "        if import_sell_edge >= threshold:",
        "            qty = min(self.take_size(position), self.sell_capacity(position), bid_volume)",
        "            if qty > 0:",
        "                orders.append(Order(self.product, best_bid, -qty))",
        "        self.add_passive_quotes(orders, fair, position, best_bid, best_ask)",
        "        return orders",
        "",
        "    def build_conversions(self, state: TradingState) -> int:",
        "        del state",
        "        if not self.params.get(\"ALLOW_POSITION_FLATTEN_CONVERSIONS\", False):",
        "            return 0",
        "        # The sign convention for conversions can vary by round; keep it disabled until confirmed.",
        "        return 0",
        "",
    ]


def _participant_mm_class_block(product: ProductSpec, spec: CompetitionSpec) -> list[str]:
    class_name = _product_class_name(product.symbol)
    block_name = _params_block_name(product.symbol)
    interpretation = _product_interpretation(product, spec)
    capability_comment = ", ".join(cap.name for cap in interpretation.recommended_capabilities) or "manual review needed"
    mechanics_comment = ", ".join(interpretation.recognized_mechanics) if interpretation.recognized_mechanics else "none declared"
    unknown_comment = ", ".join(interpretation.unknown_mechanics) if interpretation.unknown_mechanics else "none"
    return [
        f"class {class_name}(BaseProductTrader):",
        f"    # Archetype: participant_mm",
        f"    # Recommended capabilities: {capability_comment}",
        f"    # Mechanics: {mechanics_comment}",
        f"    # Unknown mechanics: {unknown_comment}",
        f"    # Fallback mode: {interpretation.fallback_mode}",
        "    def default_params(self) -> dict:",
        f"        return dict({block_name})",
        "",
        "    def participant_signal(self, state: TradingState):",
        "        product_trades = state.market_trades.get(self.product, []) if getattr(state, \"market_trades\", None) else []",
        "        return participant_flow_signal(",
        "            product_trades,",
        "            self.params.get(\"TRACKED_PARTICIPANTS\", []),",
        "            participant_weights=self.params.get(\"PARTICIPANT_WEIGHTS\", {}),",
        "        )",
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
        "        signal = self.participant_signal(state)",
        "        fair = mid",
        "        active_signal = signal.matched_volume >= int(self.params.get(\"MIN_MATCHED_VOLUME\", 1)) and abs(signal.normalized_bias) >= float(self.params.get(\"SIGNAL_THRESHOLD\", 0.25))",
        "        direction = signal.normalized_bias",
        "        follow_mode = str(self.params.get(\"FOLLOW_MODE\", \"follow\")).strip().lower()",
        "        if follow_mode == \"fade\":",
        "            direction = -direction",
        "        elif follow_mode == \"gate\" and not active_signal:",
        "            return []",
        "        if active_signal:",
        "            fair += float(self.params.get(\"SIGNAL_WEIGHT\", 2.0)) * direction * self.tick_size_value",
        "        fair -= self.params.get(\"INVENTORY_SKEW\", 0.0) * self.inventory_ratio(position) * self.tick_size_value",
        "        orders: list[Order] = []",
        "        take_edge = float(self.params.get(\"TAKE_EDGE\", 1.0))",
        "        if active_signal and direction > 0 and best_ask <= fair - take_edge:",
        "            qty = min(self.take_size(position), self.buy_capacity(position), ask_volume)",
        "            if qty > 0:",
        "                orders.append(Order(self.product, best_ask, qty))",
        "        if active_signal and direction < 0 and best_bid >= fair + take_edge:",
        "            qty = min(self.take_size(position), self.sell_capacity(position), bid_volume)",
        "            if qty > 0:",
        "                orders.append(Order(self.product, best_bid, -qty))",
        "        self.add_passive_quotes(orders, fair, position, best_bid, best_ask)",
        "        return orders",
        "",
    ]


def _signal_mm_class_block(product: ProductSpec, spec: CompetitionSpec) -> list[str]:
    class_name = _product_class_name(product.symbol)
    block_name = _params_block_name(product.symbol)
    interpretation = _product_interpretation(product, spec)
    capability_comment = ", ".join(cap.name for cap in interpretation.recommended_capabilities) or "manual review needed"
    mechanics_comment = ", ".join(interpretation.recognized_mechanics) if interpretation.recognized_mechanics else "none declared"
    unknown_comment = ", ".join(interpretation.unknown_mechanics) if interpretation.unknown_mechanics else "none"
    return [
        f"class {class_name}(BaseProductTrader):",
        f"    # Archetype: signal_mm",
        f"    # Recommended capabilities: {capability_comment}",
        f"    # Mechanics: {mechanics_comment}",
        f"    # Unknown mechanics: {unknown_comment}",
        f"    # Fallback mode: {interpretation.fallback_mode}",
        "    def default_params(self) -> dict:",
        f"        return dict({block_name})",
        "",
        "    def signal_key(self) -> str:",
        "        signal_rule = self.metadata.get(\"signal_rule\") or {}",
        "        custom_fields = self.metadata.get(\"custom_fields\", {})",
        "        explicit_source = str(signal_rule.get(\"source_key\") or custom_fields.get(\"signal_source\") or \"\").strip()",
        "        if explicit_source:",
        "            return explicit_source",
        "        signal_candidates: list[str] = []",
        "        plain_candidates: list[str] = []",
        "        for channel in self.metadata.get(\"observation_channels\", []):",
        "            if not isinstance(channel, dict):",
        "                continue",
        "            key = str(channel.get(\"key\") or \"\").strip()",
        "            kind = str(channel.get(\"kind\", \"plain\") or \"plain\").strip().lower()",
        "            role = str(channel.get(\"role\") or \"\").strip().lower()",
        "            if not key or kind != \"plain\":",
        "                continue",
        "            plain_candidates.append(key)",
        "            if role == \"signal\":",
        "                signal_candidates.append(key)",
        "        if len(signal_candidates) == 1:",
        "            return signal_candidates[0]",
        "        if len(plain_candidates) == 1:",
        "            return plain_candidates[0]",
        "        observations = self.metadata.get(\"observations\", [])",
        "        if isinstance(observations, list):",
        "            for item in observations:",
        "                key = str(item).strip()",
        "                if key:",
        "                    return key",
        "        return self.product",
        "",
        "    def external_signal_value(self, state: TradingState) -> float | None:",
        "        return self.plain_observation(state, self.signal_key())",
        "",
        "    def signal_reference(self, state: TradingState, best_bid: int, best_ask: int):",
        "        signal_value = self.external_signal_value(state)",
        "        if signal_value is None:",
        "            return None",
        "        return signal_reference_fair(",
        "            base_fair=self.mid_price(best_bid, best_ask),",
        "            signal_value=signal_value,",
        "            baseline=float(self.params.get(\"SIGNAL_BASELINE\", 0.0)),",
        "            signal_scale=float(self.params.get(\"SIGNAL_SCALE\", 1.0) or 1.0),",
        "            signal_weight=float(self.params.get(\"SIGNAL_WEIGHT\", 1.5)),",
        "            tick_size=self.tick_size_value,",
        "            max_abs_signal=self.parse_float(self.params.get(\"MAX_SIGNAL_ABS\")),",
        "        )",
        "",
        "    def build_orders(self, state: TradingState) -> list[Order]:",
        "        if not self.params.get(\"ENABLED\", True):",
        "            return []",
        "        touch = self.touch(state)",
        "        if touch is None:",
        "            return []",
        "        best_bid, bid_volume, best_ask, ask_volume = touch",
        "        reference = self.signal_reference(state, best_bid, best_ask)",
        "        if reference is None:",
        "            return []",
        "        position = self.current_position(state)",
        "        fair = reference.fair_value",
        "        fair -= self.params.get(\"INVENTORY_SKEW\", 0.0) * self.inventory_ratio(position) * self.tick_size_value",
        "        orders: list[Order] = []",
        "        take_edge = float(self.params.get(\"TAKE_EDGE\", 1.0))",
        "        signal_threshold = float(self.params.get(\"SIGNAL_THRESHOLD\", 0.15))",
        "        active_signal = abs(reference.clipped_signal) >= signal_threshold",
        "        if active_signal and best_ask <= fair - take_edge:",
        "            qty = min(self.take_size(position), self.buy_capacity(position), ask_volume)",
        "            if qty > 0:",
        "                orders.append(Order(self.product, best_ask, qty))",
        "        if active_signal and best_bid >= fair + take_edge:",
        "            qty = min(self.take_size(position), self.sell_capacity(position), bid_volume)",
        "            if qty > 0:",
        "                orders.append(Order(self.product, best_bid, -qty))",
        "        self.add_passive_quotes(orders, fair, position, best_bid, best_ask)",
        "        return orders",
        "",
    ]


def _stub_class_block(product: ProductSpec, spec: CompetitionSpec, archetype: str) -> list[str]:
    class_name = _product_class_name(product.symbol)
    block_name = _params_block_name(product.symbol)
    interpretation = _product_interpretation(product, spec)
    blueprint = _archetype_blueprint(archetype)
    capability_comment = ", ".join(cap.name for cap in interpretation.recommended_capabilities) or "manual review needed"
    mechanics_comment = ", ".join(interpretation.recognized_mechanics) if interpretation.recognized_mechanics else "none declared"
    unknown_comment = ", ".join(interpretation.unknown_mechanics) if interpretation.unknown_mechanics else "none"
    todo = {
        "derivative_stub": "Implement theoretical value, hedge logic, and expiry handling from the competition brief.",
        "spread_stub": "Implement spread fair, hedge ratios, and multi-product execution for the linked sleeve.",
        "participant_stub": "Implement participant tracking and decide whether to follow or fade informed flow.",
        "conversion_stub": "Implement conversion economics, timing, and transformed inventory accounting.",
        "auction_stub": "Implement auction timing, clearing assumptions, and pre-auction positioning.",
        "storage_stub": "Implement carry-adjusted fair value and storage-aware inventory targeting.",
        "signal_stub": "Implement external-signal extraction and map it into fair value or aggression.",
        "uncertain_stub": "Resolve the unknown mechanics and special rules before writing the first trading sleeve.",
    }[archetype]
    lines = [
        f"class {class_name}(BaseProductTrader):",
        f"    # Archetype: {archetype}",
        f"    # Recommended capabilities: {capability_comment}",
        f"    # Mechanics: {mechanics_comment}",
        f"    # Unknown mechanics: {unknown_comment}",
        f"    # Fallback mode: {interpretation.fallback_mode}",
        f"    # TODO: {todo}",
        *_render_blueprint_comments(blueprint),
        "    def default_params(self) -> dict:",
        f"        return dict({block_name})",
        "",
    ]
    if blueprint is not None:
        for method in blueprint.methods:
            lines.extend(_render_blueprint_method(method))
    lines.extend(
        [
        "    def build_orders(self, state: TradingState) -> list[Order]:",
        "        # Generated as a safe stub because this product family needs deliberate structure.",
        "        del state",
        "        return []",
        "",
        ]
    )
    return lines


def _render_product_class(product: ProductSpec, spec: CompetitionSpec) -> list[str]:
    archetype = _choose_archetype(product, spec)
    if archetype == "anchored_mm":
        return _anchored_class_block(product, spec)
    if archetype == "directional_mm":
        return _directional_class_block(product, spec)
    if archetype == "simple_mm":
        return _simple_mm_class_block(product, spec)
    if archetype == "spread_mm":
        return _spread_mm_class_block(product, spec)
    if archetype == "basket_mm":
        return _basket_mm_class_block(product, spec)
    if archetype == "derivative_mm":
        return _derivative_mm_class_block(product, spec)
    if archetype == "conversion_mm":
        return _conversion_mm_class_block(product, spec)
    if archetype == "participant_mm":
        return _participant_mm_class_block(product, spec)
    if archetype == "signal_mm":
        return _signal_mm_class_block(product, spec)
    return _stub_class_block(product, spec, archetype)


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
        product_class_blocks.extend(_render_product_class(product, spec))

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
        "from trader_factory.strategies.basket import basket_reference_fair",
        "from trader_factory.strategies.conversion import conversion_edges, conversion_reference_prices",
        "from trader_factory.strategies.derivative import black_scholes_option_reference",
        "from trader_factory.strategies.participant import participant_flow_signal",
        "from trader_factory.strategies.signal import signal_reference_fair",
        "from trader_factory.strategies.spread import linked_reference_fair",
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
        "    def order_depth_for_symbol(self, state: TradingState, symbol: str):",
        "        return state.order_depths.get(symbol)",
        "",
        "    def conversion_observation(self, state: TradingState):",
        "        observations = getattr(state, \"observations\", None)",
        "        if observations is None:",
        "            return None",
        "        conversion_observations = getattr(observations, \"conversionObservations\", None)",
        "        if not conversion_observations:",
        "            return None",
        "        return conversion_observations.get(self.product)",
        "",
        "    def plain_observation(self, state: TradingState, key: str | None = None) -> float | None:",
        "        observations = getattr(state, \"observations\", None)",
        "        if observations is None:",
        "            return None",
        "        plain_observations = getattr(observations, \"plainValueObservations\", None)",
        "        if not plain_observations:",
        "            return None",
        "        lookup_key = str(key or self.product).strip()",
        "        if not lookup_key or lookup_key not in plain_observations:",
        "            return None",
        "        return self.parse_float(plain_observations.get(lookup_key))",
        "",
        "    def touch(self, state: TradingState):",
        "        depth = self.order_depth(state)",
        "        if depth is None or not depth.buy_orders or not depth.sell_orders:",
        "            return None",
        "        best_bid = max(depth.buy_orders)",
        "        best_ask = min(depth.sell_orders)",
        "        return int(best_bid), int(depth.buy_orders[best_bid]), int(best_ask), abs(int(depth.sell_orders[best_ask]))",
        "",
        "    def touch_for_symbol(self, state: TradingState, symbol: str):",
        "        depth = self.order_depth_for_symbol(state, symbol)",
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
        "    @staticmethod",
        "    def parse_float(value) -> float | None:",
        "        if value in {None, \"\"}:",
        "            return None",
        "        try:",
        "            return float(value)",
        "        except (TypeError, ValueError):",
        "            return None",
        "",
        "    def mid_price(self, best_bid: int, best_ask: int) -> float:",
        "        return (best_bid + best_ask) / 2.0",
        "",
        "    def mid_for_symbol(self, state: TradingState, symbol: str) -> float | None:",
        "        touch = self.touch_for_symbol(state, symbol)",
        "        if touch is None:",
        "            return None",
        "        best_bid, _bid_volume, best_ask, _ask_volume = touch",
        "        return self.mid_price(best_bid, best_ask)",
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
        "    def build_conversions(self, state: TradingState) -> int:",
        "        del state",
        "        return 0",
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
        "        conversions = 0",
        "        for product, trader in self.product_traders.items():",
        "            if product in state.order_depths:",
        "                product_orders = trader.build_orders(state)",
        "                if product_orders:",
        "                    orders[product] = product_orders",
        "                conversions += int(trader.build_conversions(state))",
        "        trader_data = state.traderData if hasattr(state, \"traderData\") else \"\"",
        "        return orders, conversions, trader_data",
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
        "- `spec_validation.md`: human-readable validation report for missing inputs, unresolved questions, and legacy-field reliance",
        "- `spec_validation.json`: machine-readable validation findings for automation or agent tooling",
        "- `plan.md`: generated round plan and capability recommendations",
        "- `params.py`: product limits and metadata",
        "- `trader.py`: runnable multi-product baseline with capability-aware sleeves",
        "- `round_start_checklist.md`: mandatory intake and uncertainty checklist for this round",
        "- `experiments/`: deterministic, Monte Carlo, optimization, and official-analysis templates",
        "- `experiments/gate_policy_template.json`: starter promotion thresholds for development-mode gating",
        "- `research/`: probe suggestions and research notes",
        "- `research/structural_design_brief.md`: blueprint-driven design brief for products that need deliberate manual sleeves",
        "- `notes.md`: room for round-specific discoveries and handoff notes",
        "",
        "## Working Rule",
        "",
        "- start with the generated baseline trader",
        "- validate with deterministic replay",
        "- validate with Monte Carlo robustness",
        "- use experiment templates before inventing new workflow files",
        "- switch into research mode only when local and official behavior diverge materially",
        "- let the fixed workflow handle mapping and scaffolding, and spend agent time on unresolved mechanics and deliberate design choices",
        "",
    ]
    return "\n".join(lines)


def _render_notes(spec: CompetitionSpec) -> str:
    interpretations = interpret_competition(spec)
    lines = [
        "# Notes",
        "",
        "Use this file to record round-specific discoveries.",
        "",
        "Initial checklist:",
        "- confirm product mechanics against the actual competition brief and update `spec.json` when labels or rules change",
        "- confirm which generated archetypes are acceptable and which need manual redesign",
        "- resolve any `manual_review_required` or `manual_design_required` products before promotion",
        "- run deterministic replay and capture baseline scores before touching optimization configs",
        "- decide whether the next step is development mode or research mode",
        "",
        "Products:",
    ]
    for product in spec.products:
        interpretation = interpretations[product.symbol]
        summary = product.notes or "no extra notes yet"
        lines.append(
            f"- {product.symbol}: archetype `{interpretation.preferred_archetype}`, fallback `{interpretation.fallback_mode}`. {summary}"
        )
        blueprint = _archetype_blueprint(interpretation.preferred_archetype)
        if blueprint is not None:
            lines.append(f"  Blueprint summary: {blueprint.summary}")
        if interpretation.open_questions:
            lines.append(f"  Open questions: {', '.join(interpretation.open_questions)}")
        if interpretation.intake_gaps:
            lines.append(f"  Intake gaps: {', '.join(interpretation.intake_gaps)}")
    lines.append("")
    return "\n".join(lines)


def _render_round_start_checklist(spec: CompetitionSpec) -> str:
    interpretations = interpret_competition(spec)
    lines = [
        "# Round Start Checklist",
        "",
        "TraderFactory is intended to reduce mechanical work for the agent, not to hide uncertainty.",
        "Use this checklist at round open before relying on generated sleeves.",
        "",
        "## Mandatory Inputs",
        "",
        "- confirm product list, position limits, and tick sizes",
        "- classify each product into recognized mechanic labels where possible",
        "- record any unclear mechanics under `unknown_mechanics` instead of guessing",
        "- encode explicit relationships, settlement rules, and pricing inputs when products are linked or nonlinear",
        "- note whether execution should be treated as maker, taker, or mixed",
        "",
    ]
    if spec.unknown_mechanics or spec.open_questions or spec.special_rules:
        lines.extend(
            [
                "## Round-Level Uncertainty",
                "",
                f"- Unknown mechanics: {', '.join(spec.unknown_mechanics) or 'none'}",
                f"- Open questions: {', '.join(spec.open_questions) or 'none'}",
                f"- Special rules: {', '.join(rule.name or rule.description for rule in spec.special_rules) or 'none'}",
                "",
            ]
        )
    lines.extend(
        [
        "## Product Review",
        "",
        ]
    )
    for product in spec.products:
        interpretation = interpretations[product.symbol]
        blueprint = _archetype_blueprint(interpretation.preferred_archetype)
        lines.extend(
            [
                f"### {product.symbol}",
                "",
                f"- Generated archetype: `{interpretation.preferred_archetype}`",
                f"- Fallback mode: `{interpretation.fallback_mode}`",
                f"- Recognized mechanics: {', '.join(interpretation.recognized_mechanics) or 'none'}",
                f"- Unknown mechanics: {', '.join(interpretation.unknown_mechanics) or 'none'}",
                f"- Related products: {', '.join(interpretation.related_products) or 'none'}",
                f"- Special rules: {', '.join(interpretation.special_rules) or 'none'}",
                f"- Research triggers: {', '.join(interpretation.research_triggers) or 'none'}",
                "",
            ]
        )
        if blueprint is not None:
            lines.append("Blueprint requirements:")
            for item in blueprint.required_inputs:
                lines.append(f"- {item}")
            lines.append("")
        if interpretation.intake_gaps:
            lines.append("Open items:")
            for gap in interpretation.intake_gaps:
                lines.append(f"- {gap}")
            lines.append("")
        if interpretation.open_questions:
            lines.append("Questions to answer:")
            for question in interpretation.open_questions:
                lines.append(f"- {question}")
            lines.append("")
    lines.extend(
        [
            "## Operating Rule",
            "",
            "- if a product is `manual_review_required`, do not optimize yet; finish the intake first",
            "- if a product is `manual_design_required`, use the generated stub as structure only and implement the missing sleeve deliberately",
            "- if a product is `research_overlay`, keep development work separate from probe work",
            "- only move into optimization after deterministic replay is stable and the intake gaps for that product are understood",
            "",
        ]
    )
    return "\n".join(lines)


def _render_experiments_readme(project_name: str, spec: CompetitionSpec) -> str:
    interpretations = interpret_competition(spec)
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
        interpretation = interpretations[product.symbol]
        blueprint = _archetype_blueprint(interpretation.preferred_archetype)
        lines.append(
            f"- `{product.symbol}`: archetype `{interpretation.preferred_archetype}` with capabilities {', '.join(cap.name for cap in interpretation.recommended_capabilities) or 'manual review needed'}"
        )
        if blueprint is not None:
            lines.append(f"  Structural blueprint: {blueprint.summary}")
        if interpretation.intake_gaps:
            lines.append(f"  Gate: resolve {', '.join(interpretation.intake_gaps)} before treating optimization as decisive.")
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
    if archetype == "spread_mm":
        return [
            {"name": "SPREAD_THRESHOLD", "lower": 0.3, "upper": 2.0},
            {"name": "QUOTE_EDGE", "lower": 0.8, "upper": 3.5},
            {"name": "REFERENCE_WEIGHT", "lower": 0.2, "upper": 1.0},
            {"name": "SPREAD_OFFSET", "lower": -3.0, "upper": 3.0},
            {"name": "INVENTORY_SKEW", "lower": 0.0, "upper": 1.0},
        ]
    if archetype == "basket_mm":
        return [
            {"name": "BASKET_THRESHOLD", "lower": 0.3, "upper": 2.5},
            {"name": "QUOTE_EDGE", "lower": 0.8, "upper": 4.0},
            {"name": "REFERENCE_WEIGHT", "lower": 0.4, "upper": 1.0},
            {"name": "PREMIUM_OFFSET", "lower": -5.0, "upper": 5.0},
            {"name": "INVENTORY_SKEW", "lower": 0.0, "upper": 1.0},
        ]
    if archetype == "derivative_mm":
        return [
            {"name": "TAKE_EDGE", "lower": 0.4, "upper": 2.5},
            {"name": "QUOTE_EDGE", "lower": 0.8, "upper": 4.0},
            {"name": "THEORETICAL_WEIGHT", "lower": 0.5, "upper": 1.0},
            {"name": "INVENTORY_SKEW", "lower": 0.0, "upper": 1.0},
        ]
    if archetype == "conversion_mm":
        return [
            {"name": "ARB_THRESHOLD", "lower": 0.3, "upper": 3.0},
            {"name": "QUOTE_EDGE", "lower": 0.8, "upper": 4.0},
            {"name": "REFERENCE_WEIGHT", "lower": 0.2, "upper": 1.0},
            {"name": "EXTRA_CONVERSION_FEE", "lower": 0.0, "upper": 3.0},
            {"name": "INVENTORY_SKEW", "lower": 0.0, "upper": 1.0},
        ]
    if archetype == "participant_mm":
        return [
            {"name": "TAKE_EDGE", "lower": 0.4, "upper": 2.0},
            {"name": "QUOTE_EDGE", "lower": 0.8, "upper": 4.0},
            {"name": "SIGNAL_THRESHOLD", "lower": 0.05, "upper": 0.9},
            {"name": "SIGNAL_WEIGHT", "lower": 0.5, "upper": 4.0},
            {"name": "INVENTORY_SKEW", "lower": 0.0, "upper": 1.2},
        ]
    if archetype == "signal_mm":
        return [
            {"name": "TAKE_EDGE", "lower": 0.4, "upper": 2.0},
            {"name": "QUOTE_EDGE", "lower": 0.8, "upper": 4.0},
            {"name": "SIGNAL_WEIGHT", "lower": 0.2, "upper": 5.0},
            {"name": "SIGNAL_SCALE", "lower": 0.2, "upper": 5.0},
            {"name": "SIGNAL_THRESHOLD", "lower": 0.0, "upper": 1.5},
            {"name": "INVENTORY_SKEW", "lower": 0.0, "upper": 1.2},
        ]
    return []


def _render_cmaes_template(product: ProductSpec, spec: CompetitionSpec) -> str | None:
    archetype = _choose_archetype(product, spec)
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


def _render_gate_policy_template(spec: CompetitionSpec) -> str:
    interpretations = interpret_competition(spec)
    structural_products = [
        product.symbol
        for product in spec.products
        if _archetype_blueprint(interpretations[product.symbol].preferred_archetype) is not None
    ]
    payload = {
        "round_id": 1,
        "require_deterministic": True,
        "require_monte_carlo": True,
        "deterministic_min_total_delta": 0.0,
        "mc_min_mean_delta": 0.0,
        "mc_min_p10_delta": None,
        "mc_min_plausible_mean_delta": 0.0,
        "mc_min_plausible_p10_delta": None,
        "notes": (
            "Template gate policy for this scaffolded project. "
            + (
                "Structural products are present: "
                + ", ".join(structural_products)
                + ". Do not promote them only on gate results before the design brief is resolved."
                if structural_products
                else "Adjust thresholds after the first trustworthy baseline run."
            )
        ),
    }
    return json.dumps(payload, indent=2) + "\n"


def _render_structural_design_brief(spec: CompetitionSpec) -> str:
    interpretations = interpret_competition(spec)
    lines = [
        "# Structural Design Brief",
        "",
        "This file exists for products whose generated archetype is intentionally only a structural starting point.",
        "Use it to move from scaffold to deliberate sleeve design without losing the reasoning trail.",
        "",
    ]
    any_structural = False
    for product in spec.products:
        interpretation = interpretations[product.symbol]
        blueprint = _archetype_blueprint(interpretation.preferred_archetype)
        if blueprint is None:
            continue
        any_structural = True
        lines.extend(
            [
                f"## {product.symbol}",
                "",
                f"- Archetype: `{interpretation.preferred_archetype}`",
                f"- Fallback mode: `{interpretation.fallback_mode}`",
                f"- Blueprint summary: {blueprint.summary}",
                "",
                "Required inputs:",
            ]
        )
        for item in blueprint.required_inputs:
            lines.append(f"- {item}")
        lines.extend(["", "Design questions:"])
        for question in blueprint.design_questions:
            lines.append(f"- {question}")
        lines.extend(["", "Implementation TODOs:"])
        for todo in blueprint.implementation_todos:
            lines.append(f"- {todo}")
        if blueprint.custom_field_examples:
            lines.extend(["", "Suggested custom_fields:"])
            for field_name in blueprint.custom_field_examples:
                lines.append(f"- `{field_name}`")
        if blueprint.research_prompts:
            lines.extend(["", "Research prompts:"])
            for prompt in blueprint.research_prompts:
                lines.append(f"- {prompt}")
        if interpretation.intake_gaps:
            lines.extend(["", "Current intake gaps:"])
            for gap in interpretation.intake_gaps:
                lines.append(f"- {gap}")
        lines.append("")
    if not any_structural:
        lines.append("No products currently require a structural design brief from the generated archetypes.")
        lines.append("")
    return "\n".join(lines)


def _render_research_readme(spec: CompetitionSpec) -> str:
    interpretations = interpret_competition(spec)
    lines = [
        "# Research",
        "",
        "Use this directory when development mode is not enough.",
        "Use `structural_design_brief.md` when the generated project contains deliberate manual stubs.",
        "",
        "Switch into research mode when:",
        "",
        "- local replay and official submissions diverge materially",
        "- a candidate feature appears dormant",
        "- passive or aggressive execution behavior is unclear",
        "- a structural product needs deliberate design beyond the generated stub",
        "",
        "Probe targets from this spec:",
    ]
    flagged = False
    for product in spec.products:
        interpretation = interpretations[product.symbol]
        capabilities = {cap.name for cap in interpretation.recommended_capabilities}
        if "execution_probe_suite" in capabilities or interpretation.research_triggers:
            flagged = True
            lines.extend(
                [
                    f"- `{product.symbol}`",
                    f"  - fallback: `{interpretation.fallback_mode}`",
                    f"  - triggers: {', '.join(interpretation.research_triggers) or 'none'}",
                ]
            )
            if interpretation.unknown_mechanics:
                lines.append(f"  - unknown mechanics: {', '.join(interpretation.unknown_mechanics)}")
    if not flagged:
        lines.append("- No products were explicitly flagged for execution research from the current spec.")
    lines.append("")
    return "\n".join(lines)


def _render_probe_targets(spec: CompetitionSpec) -> str:
    interpretations = interpret_competition(spec)
    lines = [
        "# Probe Targets",
        "",
        "Use this file to decide when a generated project should switch from development mode to research mode.",
        "",
    ]
    for product in spec.products:
        interpretation = interpretations[product.symbol]
        capabilities = {cap.name for cap in interpretation.recommended_capabilities}
        blueprint = _archetype_blueprint(interpretation.preferred_archetype)
        lines.append(f"## {product.symbol}")
        lines.append("")
        if "execution_probe_suite" in capabilities or interpretation.research_triggers:
            lines.extend(
                [
                    "- Suggested first probes:",
                ]
            )
            for trigger in interpretation.research_triggers:
                if trigger == "boundary":
                    lines.append(f"  - `python3 -m trader_factory.cli probe-scaffold boundary ./trader.py --product {product.symbol}`")
                elif trigger == "aggressive_markout":
                    lines.append(
                        f"  - `python3 -m trader_factory.cli probe-scaffold aggressive_markout ./trader.py --product {product.symbol} --context range_buy`"
                    )
                elif trigger == "passive_ladder":
                    lines.append(f"  - `python3 -m trader_factory.cli probe-scaffold passive_ladder ./trader.py --product {product.symbol}`")
            lines.extend(
                [
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "- No immediate probe recommendation from the current mechanics.",
                    f"- Fallback mode: `{interpretation.fallback_mode}`.",
                    f"- Structural blueprint: {blueprint.summary}" if blueprint is not None else "- Structural blueprint: none.",
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
    validation_report = validate_competition_spec(spec)
    name = project_name or _project_slug(spec)
    workspace = Path(output_dir).expanduser().resolve() if output_dir else (Path.cwd() / name).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    readme_path = workspace / "README.md"
    spec_copy_path = workspace / "spec.json"
    spec_validation_path = workspace / "spec_validation.md"
    spec_validation_json_path = workspace / "spec_validation.json"
    plan_path = workspace / "plan.md"
    trader_path = workspace / "trader.py"
    params_path = workspace / "params.py"
    notes_path = workspace / "notes.md"
    round_start_checklist_path = workspace / "round_start_checklist.md"
    experiments_dir = workspace / "experiments"
    research_dir = workspace / "research"
    structural_design_brief_path = research_dir / "structural_design_brief.md"
    gate_policy_template_path = experiments_dir / "gate_policy_template.json"

    experiments_dir.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)

    readme_path.write_text(_render_readme(spec, name) + "\n")
    spec_copy_path.write_text(json.dumps(json.loads(spec_file.read_text()), indent=2) + "\n")
    spec_validation_path.write_text(render_validation_markdown(validation_report) + "\n")
    spec_validation_json_path.write_text(json.dumps(validation_report.to_dict(), indent=2) + "\n")
    plan_path.write_text(render_markdown_plan(spec))
    trader_path.write_text(_render_trader(spec))
    params_path.write_text(_render_params(spec))
    notes_path.write_text(_render_notes(spec))
    round_start_checklist_path.write_text(_render_round_start_checklist(spec) + "\n")
    (experiments_dir / "README.md").write_text(_render_experiments_readme(name, spec) + "\n")
    gate_policy_template_path.write_text(_render_gate_policy_template(spec))
    (research_dir / "README.md").write_text(_render_research_readme(spec) + "\n")
    (research_dir / "probe_targets.md").write_text(_render_probe_targets(spec) + "\n")
    structural_design_brief_path.write_text(_render_structural_design_brief(spec) + "\n")

    for product in spec.products:
        template = _render_cmaes_template(product, spec)
        if template is not None:
            (experiments_dir / f"cmaes_template_{product.symbol.lower()}.json").write_text(template)

    return TraderProjectResult(
        project_name=name,
        output_dir=workspace,
        readme_path=readme_path,
        spec_copy_path=spec_copy_path,
        spec_validation_path=spec_validation_path,
        spec_validation_json_path=spec_validation_json_path,
        plan_path=plan_path,
        trader_path=trader_path,
        params_path=params_path,
        notes_path=notes_path,
        round_start_checklist_path=round_start_checklist_path,
        experiments_dir=experiments_dir,
        research_dir=research_dir,
        structural_design_brief_path=structural_design_brief_path,
        gate_policy_template_path=gate_policy_template_path,
    )
