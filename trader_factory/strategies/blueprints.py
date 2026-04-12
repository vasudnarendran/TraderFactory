from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BlueprintMethod:
    signature: str
    body_lines: list[str] = field(default_factory=list)
    summary: str = ""


@dataclass(slots=True)
class ArchetypeBlueprint:
    name: str
    summary: str
    category: str
    required_inputs: list[str] = field(default_factory=list)
    custom_field_examples: list[str] = field(default_factory=list)
    design_questions: list[str] = field(default_factory=list)
    implementation_todos: list[str] = field(default_factory=list)
    research_prompts: list[str] = field(default_factory=list)
    default_params: list[tuple[str, Any]] = field(default_factory=list)
    methods: list[BlueprintMethod] = field(default_factory=list)


ARCHETYPE_BLUEPRINTS: dict[str, ArchetypeBlueprint] = {
    "spread_stub": ArchetypeBlueprint(
        name="spread_stub",
        category="linked_products",
        summary="Residual or hedge-based sleeve for linked products, spreads, or baskets.",
        required_inputs=[
            "related products",
            "hedge ratios or component weights",
            "spread definition or residual formula",
            "cross-product execution rule",
        ],
        custom_field_examples=["hedge_ratio", "components", "spread_formula"],
        design_questions=[
            "What is the exact spread or basket definition?",
            "Should execution leg sequentially, jointly, or with one-sided probing?",
            "How much hedge slippage is acceptable before aborting the trade?",
        ],
        implementation_todos=[
            "Define a spread fair or residual value from linked products.",
            "Encode hedge sizing explicitly rather than inferring it from position limits.",
            "Separate alpha generation from leg-execution logic.",
        ],
        research_prompts=[
            "Validate whether legging risk or passive fill mismatch dominates the spread edge.",
        ],
        default_params=[
            ("ENABLED", True),
            ("SPREAD_THRESHOLD", 1.0),
            ("MAX_SPREAD_SIZE", 1),
            ("HEDGE_RATIO", 1.0),
            ("TODO_NOTE", "Replace placeholder spread parameters with round-specific residual logic."),
        ],
        methods=[
            BlueprintMethod(
                signature="def linked_symbols(self) -> list[str]:",
                body_lines=["return list(self.metadata.get(\"related_products\", []))"],
                summary="Return the linked symbols from metadata.",
            ),
            BlueprintMethod(
                signature="def spread_fair(self, state: TradingState) -> float | None:",
                body_lines=["del state", "return None"],
                summary="Compute the target spread fair or residual anchor.",
            ),
            BlueprintMethod(
                signature="def hedge_plan(self, state: TradingState) -> dict[str, int]:",
                body_lines=["del state", "return {}"],
                summary="Return per-symbol hedge targets once the residual model exists.",
            ),
        ],
    ),
    "derivative_stub": ArchetypeBlueprint(
        name="derivative_stub",
        category="pricing",
        summary="Pricing-model sleeve for derivatives or nonlinear payoff products.",
        required_inputs=[
            "underlying definition",
            "payoff or settlement formula",
            "strike and expiry if relevant",
            "hedge convention",
        ],
        custom_field_examples=["underlying", "strike", "expiry", "settlement_formula", "carry_assumptions"],
        design_questions=[
            "What is the exact theoretical value formula for this contract?",
            "Does the official simulator require explicit hedge execution or only valuation-aware quoting?",
            "Which inputs are state variables and which are static contract terms?",
        ],
        implementation_todos=[
            "Implement theoretical value before any quoting logic.",
            "Encode hedge sensitivity or hedge target explicitly.",
            "Separate pricing, execution, and expiry handling in the final sleeve.",
        ],
        research_prompts=[
            "Check whether hedge latency or settlement mismatch dominates the transfer gap.",
        ],
        default_params=[
            ("ENABLED", True),
            ("FAIR_EDGE", 1.0),
            ("MAX_TAKE_SIZE", 1),
            ("HEDGE_RATIO", 1.0),
            ("TODO_NOTE", "Fill in the pricing inputs and hedge logic for this contract."),
        ],
        methods=[
            BlueprintMethod(
                signature="def underlying_symbol(self) -> str | None:",
                body_lines=["return self.metadata.get(\"custom_fields\", {}).get(\"underlying\")"],
                summary="Read the underlying symbol from metadata when present.",
            ),
            BlueprintMethod(
                signature="def theoretical_value(self, state: TradingState) -> float | None:",
                body_lines=["del state", "return None"],
                summary="Implement contract pricing here.",
            ),
            BlueprintMethod(
                signature="def hedge_orders(self, state: TradingState) -> list[Order]:",
                body_lines=["del state", "return []"],
                summary="Build hedge orders once the pricing model is known.",
            ),
        ],
    ),
    "participant_stub": ArchetypeBlueprint(
        name="participant_stub",
        category="participant_flow",
        summary="Participant-aware sleeve for named, informed, or privileged flow.",
        required_inputs=[
            "participant identifier semantics",
            "participant visibility in the feed",
            "follow vs fade rules",
        ],
        custom_field_examples=["tracked_participants", "signal_horizon", "follow_mode"],
        design_questions=[
            "Do we follow, fade, or gate on specific participants?",
            "How long does a participant signal remain live?",
            "What prevents stale or late participant reactions?",
        ],
        implementation_todos=[
            "Define participant signal extraction separately from trading decisions.",
            "Encode signal decay and stale-signal invalidation.",
            "Gate inventory risk when participant flow is one-sided.",
        ],
        research_prompts=[
            "Measure whether participant signals survive enough time to justify following.",
        ],
        default_params=[
            ("ENABLED", True),
            ("FOLLOW_THRESHOLD", 1.0),
            ("FADE_THRESHOLD", 1.0),
            ("MAX_SIGNAL_AGE", 3),
            ("TODO_NOTE", "Define participant semantics and the follow-or-fade policy."),
        ],
        methods=[
            BlueprintMethod(
                signature="def participant_signal(self, state: TradingState) -> float:",
                body_lines=["del state", "return 0.0"],
                summary="Extract the current participant-driven bias.",
            ),
            BlueprintMethod(
                signature="def signal_is_fresh(self, signal_age: int) -> bool:",
                body_lines=["return signal_age <= int(self.params.get(\"MAX_SIGNAL_AGE\", 0))"],
                summary="Keep stale participant signals from leaking into execution.",
            ),
        ],
    ),
    "conversion_stub": ArchetypeBlueprint(
        name="conversion_stub",
        category="conversions",
        summary="Conversion or transport sleeve for products that can be transformed or moved.",
        required_inputs=[
            "conversion ratio",
            "fees or penalties",
            "timing or latency of conversion",
            "capacity or lot-size restrictions",
        ],
        custom_field_examples=["conversion_ratio", "conversion_fee", "transport_delay", "lot_size"],
        design_questions=[
            "Is conversion immediate, delayed, or capacity constrained?",
            "Does conversion create inventory in another product or location?",
            "Should trading and conversion be optimized jointly or sequentially?",
        ],
        implementation_todos=[
            "Encode the conversion economics directly from the brief.",
            "Track pre- and post-conversion inventory separately if needed.",
            "Treat conversion as part of valuation, not only as a post-trade cleanup step.",
        ],
        research_prompts=[
            "Check whether conversion timing or simulator semantics materially affect profitability.",
        ],
        default_params=[
            ("ENABLED", True),
            ("MIN_CONVERSION_EDGE", 1.0),
            ("MAX_CONVERSION_SIZE", 1),
            ("CONVERSION_FEE", 0.0),
            ("TODO_NOTE", "Fill in the conversion economics and timing rules."),
        ],
        methods=[
            BlueprintMethod(
                signature="def conversion_edge(self, state: TradingState) -> float | None:",
                body_lines=["del state", "return None"],
                summary="Return the edge from converting instead of directly trading.",
            ),
            BlueprintMethod(
                signature="def conversion_plan(self, state: TradingState) -> dict[str, int]:",
                body_lines=["del state", "return {}"],
                summary="Describe how inventory should move across products or states.",
            ),
        ],
    ),
    "auction_stub": ArchetypeBlueprint(
        name="auction_stub",
        category="auctions",
        summary="Auction-style sleeve for products with discrete clearing or scheduled matching.",
        required_inputs=[
            "auction timing",
            "clearing rule",
            "price formation rule",
            "pre-auction information channels",
        ],
        custom_field_examples=["auction_schedule", "clearing_rule", "pre_open_window"],
        design_questions=[
            "How is the auction cleared and when can orders be adjusted?",
            "Should inventory be accumulated ahead of the auction or only expressed at the event?",
            "What information matters most near the clearing time?",
        ],
        implementation_todos=[
            "Encode the auction timeline first.",
            "Separate pre-auction positioning from the final auction submission.",
            "Gate order size on clearing uncertainty.",
        ],
        research_prompts=[
            "Validate whether auction timing and state visibility are fully represented in local replay.",
        ],
        default_params=[
            ("ENABLED", True),
            ("AUCTION_EDGE", 1.0),
            ("MAX_AUCTION_SIZE", 1),
            ("PREP_WINDOW", 10),
            ("TODO_NOTE", "Replace the placeholder auction timing and clearing assumptions."),
        ],
        methods=[
            BlueprintMethod(
                signature="def auction_target(self, state: TradingState) -> tuple[int, int] | None:",
                body_lines=["del state", "return None"],
                summary="Return the desired auction price and size.",
            ),
            BlueprintMethod(
                signature="def in_prep_window(self, state: TradingState) -> bool:",
                body_lines=["del state", "return False"],
                summary="Decide whether the strategy is inside the pre-auction preparation window.",
            ),
        ],
    ),
    "storage_stub": ArchetypeBlueprint(
        name="storage_stub",
        category="carry_and_storage",
        summary="Carry-aware sleeve for storage, transport, or inventory-aging products.",
        required_inputs=[
            "carry cost or storage value",
            "inventory ageing or persistence rule",
            "transport or holding constraint",
        ],
        custom_field_examples=["carry_cost", "storage_limit", "inventory_decay", "transport_delay"],
        design_questions=[
            "What is the value of holding one more unit into the next state?",
            "Does inventory age, decay, or incur explicit costs?",
            "How should rebalancing trade off immediate edge against future optionality?",
        ],
        implementation_todos=[
            "Build a carry-adjusted fair value.",
            "Track target inventory rather than only flat price edge.",
            "Encode storage or transport limits in the sizing logic.",
        ],
        research_prompts=[
            "Check whether carry assumptions are robust under different simulated paths.",
        ],
        default_params=[
            ("ENABLED", True),
            ("TARGET_INVENTORY", 0),
            ("CARRY_PENALTY", 0.0),
            ("MAX_REBALANCE_SIZE", 1),
            ("TODO_NOTE", "Fill in carry economics and storage constraints."),
        ],
        methods=[
            BlueprintMethod(
                signature="def carry_adjustment(self, state: TradingState) -> float:",
                body_lines=["del state", "return 0.0"],
                summary="Return the carry or storage adjustment to fair value.",
            ),
            BlueprintMethod(
                signature="def target_inventory(self, state: TradingState) -> int:",
                body_lines=["del state", "return int(self.params.get(\"TARGET_INVENTORY\", 0))"],
                summary="Return the desired inventory target under the storage model.",
            ),
        ],
    ),
    "signal_stub": ArchetypeBlueprint(
        name="signal_stub",
        category="external_signal",
        summary="Signal-integration sleeve for products driven by external or latent observation channels.",
        required_inputs=[
            "signal definition",
            "signal latency",
            "signal scaling into fair value or aggression",
        ],
        custom_field_examples=["signal_source", "signal_weight", "signal_latency"],
        design_questions=[
            "Is the signal a fair-value input, a regime flag, or an execution gate?",
            "How stale can the signal become before it should be ignored?",
            "Should the signal shift fair value, size, or both?",
        ],
        implementation_todos=[
            "Define the external signal extraction path.",
            "Translate the signal into a fair or aggression adjustment explicitly.",
            "Gate size on signal freshness and confidence.",
        ],
        research_prompts=[
            "Measure whether the signal survives latency and execution noise.",
        ],
        default_params=[
            ("ENABLED", True),
            ("SIGNAL_WEIGHT", 1.0),
            ("SIGNAL_DECAY", 1.0),
            ("MAX_TAKE_SIZE", 1),
            ("TODO_NOTE", "Define how the external signal modifies fair value or aggression."),
        ],
        methods=[
            BlueprintMethod(
                signature="def external_signal_value(self, state: TradingState) -> float | None:",
                body_lines=["del state", "return None"],
                summary="Return the current normalized signal value.",
            ),
            BlueprintMethod(
                signature="def adjusted_fair(self, state: TradingState) -> float | None:",
                body_lines=["del state", "return None"],
                summary="Translate the external signal into a tradable fair value.",
            ),
        ],
    ),
    "uncertain_stub": ArchetypeBlueprint(
        name="uncertain_stub",
        category="unknown",
        summary="Safety-first placeholder for products whose mechanics are still structurally unresolved.",
        required_inputs=["mechanic classification", "pricing rule", "execution rule"],
        custom_field_examples=["open_questions", "brief_excerpt"],
        design_questions=[
            "Which mechanic family is actually present here?",
            "What missing rule would change the architecture choice?",
            "What evidence is needed before writing the first sleeve?",
        ],
        implementation_todos=[
            "Resolve the mechanic classification before trading logic is written.",
            "Promote the product into a concrete archetype only after the intake gaps are closed.",
        ],
        research_prompts=[
            "Do not probe for alpha until the basic mechanic classification is settled.",
        ],
        default_params=[
            ("ENABLED", True),
            ("TODO_NOTE", "Resolve the unknown mechanics before implementing trading logic."),
        ],
        methods=[
            BlueprintMethod(
                signature="def unresolved_items(self) -> list[str]:",
                body_lines=["return list(self.metadata.get(\"intake_gaps\", []))"],
                summary="Expose unresolved intake gaps inside the generated stub.",
            ),
        ],
    ),
}


def get_archetype_blueprint(name: str) -> ArchetypeBlueprint | None:
    return ARCHETYPE_BLUEPRINTS.get(name)
