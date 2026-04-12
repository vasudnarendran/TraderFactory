from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from trader_factory.core.mapping import interpret_product
from trader_factory.core.specs import CompetitionSpec, ProductSpec

SEVERITY_ORDER = ("error", "warning", "info")

DERIVATIVE_MECHANICS = {"option", "derivative", "expiry", "settlement_formula", "nonlinear_payoff", "volatility_surface"}
CONVERSION_MECHANICS = {"conversion", "transport", "convertible"}
AUCTION_MECHANICS = {"auction"}
PARTICIPANT_MECHANICS = {"informed_trader", "named_participant", "flow_following"}
SIGNAL_MECHANICS = {"external_signal", "multi_signal"}
BASKET_MECHANICS = {"basket"}

LEGACY_SCHEMA_KEYS: dict[str, set[str]] = {
    "basket_definition": {"components", "basket_divisor", "divisor", "fair_offset"},
    "participant_rule": {"tracked_participants", "follow_mode", "participant_weights", "signal_horizon", "max_signal_age"},
    "signal_rule": {"signal_source", "source_key", "signal_latency", "latency_hint", "staleness_limit", "interpretation_mode", "mode"},
    "derivative_contract": {
        "underlying",
        "strike",
        "option_kind",
        "option_type",
        "time_to_expiry_years",
        "expiry_years",
        "days_to_expiry",
        "expiry_days",
        "time_to_expiry_days",
        "volatility",
        "implied_volatility",
        "volatility_percent",
        "risk_free_rate",
        "carry_rate",
        "dividend_yield",
        "settlement_formula",
        "expiry_style",
        "contract_size",
    },
    "conversion_rule": {
        "ratio",
        "conversion_ratio",
        "fee",
        "conversion_fee",
        "delay_steps",
        "transport_delay",
        "lot_size",
        "source_product",
        "target_product",
        "target_symbol",
        "price_observation_key",
        "observation_key",
    },
    "auction_rule": {
        "schedule",
        "auction_schedule",
        "clearing_rule",
        "prep_window",
        "pre_open_window",
        "submission_window",
        "visibility",
        "visible_inputs",
    },
}


def _format_list(values: list[str]) -> str:
    if not values:
        return "none"
    return ", ".join(values)


def _sorted_findings(findings: list["ValidationFinding"]) -> list["ValidationFinding"]:
    return sorted(findings, key=lambda finding: (SEVERITY_ORDER.index(finding.severity), finding.code, finding.message))


@dataclass(slots=True)
class ValidationFinding:
    code: str
    severity: str
    message: str
    recommendation: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "recommendation": self.recommendation,
            "evidence": dict(self.evidence),
        }


@dataclass(slots=True)
class ProductValidationReport:
    symbol: str
    preferred_archetype: str
    fallback_mode: str
    findings: list[ValidationFinding] = field(default_factory=list)

    @property
    def status(self) -> str:
        if any(finding.severity == "error" for finding in self.findings):
            return "blocked"
        if any(finding.severity == "warning" for finding in self.findings):
            return "needs_review"
        return "ready"

    def counts_by_severity(self) -> dict[str, int]:
        counts = {severity: 0 for severity in SEVERITY_ORDER}
        for finding in self.findings:
            counts[finding.severity] = counts.get(finding.severity, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "preferred_archetype": self.preferred_archetype,
            "fallback_mode": self.fallback_mode,
            "status": self.status,
            "counts": self.counts_by_severity(),
            "findings": [finding.to_dict() for finding in _sorted_findings(self.findings)],
        }


@dataclass(slots=True)
class CompetitionValidationReport:
    competition_name: str
    round_name: str
    round_findings: list[ValidationFinding] = field(default_factory=list)
    product_reports: list[ProductValidationReport] = field(default_factory=list)

    def counts_by_severity(self) -> dict[str, int]:
        counts = {severity: 0 for severity in SEVERITY_ORDER}
        for finding in self.round_findings:
            counts[finding.severity] = counts.get(finding.severity, 0) + 1
        for report in self.product_reports:
            for severity, value in report.counts_by_severity().items():
                counts[severity] = counts.get(severity, 0) + value
        return counts

    def product_status_counts(self) -> dict[str, int]:
        counts = {"blocked": 0, "needs_review": 0, "ready": 0}
        for report in self.product_reports:
            counts[report.status] = counts.get(report.status, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "competition_name": self.competition_name,
            "round_name": self.round_name,
            "counts": self.counts_by_severity(),
            "product_status_counts": self.product_status_counts(),
            "round_findings": [finding.to_dict() for finding in _sorted_findings(self.round_findings)],
            "product_reports": [report.to_dict() for report in self.product_reports],
        }


def _legacy_schema_usage(product: ProductSpec) -> list[tuple[str, list[str]]]:
    usages: list[tuple[str, list[str]]] = []
    custom_keys = set(product.custom_fields)
    for schema_name, schema_keys in LEGACY_SCHEMA_KEYS.items():
        matched = sorted(custom_keys & schema_keys)
        if matched:
            usages.append((schema_name, matched))
    return usages


def _available_observation_keys(product: ProductSpec) -> set[str]:
    keys = set(product.observation_keys())
    for item in product.observations:
        cleaned = str(item).strip()
        if cleaned:
            keys.add(cleaned)
    return keys


def _signal_candidates(product: ProductSpec) -> tuple[list[str], list[str]]:
    signal_candidates = product.observation_keys(kind="plain", role="signal")
    plain_candidates = product.observation_keys(kind="plain")
    return signal_candidates, plain_candidates


def _finding(
    findings: list[ValidationFinding],
    *,
    code: str,
    severity: str,
    message: str,
    recommendation: str = "",
    evidence: dict[str, Any] | None = None,
) -> None:
    findings.append(
        ValidationFinding(
            code=code,
            severity=severity,
            message=message,
            recommendation=recommendation,
            evidence={} if evidence is None else dict(evidence),
        )
    )


def _validate_product(
    product: ProductSpec,
    spec: CompetitionSpec,
    *,
    declared_symbols: set[str],
) -> ProductValidationReport:
    interpretation = interpret_product(product, spec)
    findings: list[ValidationFinding] = []
    mechanics = set(product.mechanics)
    observation_keys = _available_observation_keys(product)
    signal_candidates, plain_candidates = _signal_candidates(product)

    if product.position_limit <= 0:
        _finding(
            findings,
            code="product.invalid_position_limit",
            severity="error",
            message=f"{product.symbol} has a nonpositive position limit: {product.position_limit}.",
            recommendation="Set `position_limit` to a positive integer before generation or optimization.",
            evidence={"position_limit": product.position_limit},
        )
    if product.tick_size <= 0:
        _finding(
            findings,
            code="product.invalid_tick_size",
            severity="error",
            message=f"{product.symbol} has a nonpositive tick size: {product.tick_size}.",
            recommendation="Set `tick_size` to a positive price increment.",
            evidence={"tick_size": product.tick_size},
        )
    if not product.mechanics:
        _finding(
            findings,
            code="product.missing_mechanics",
            severity="warning",
            message=f"{product.symbol} does not declare any mechanics.",
            recommendation="Classify the product with explicit mechanic labels so archetype selection is intentional.",
        )
    if product.unknown_mechanics:
        _finding(
            findings,
            code="product.unknown_mechanics",
            severity="warning",
            message=f"{product.symbol} still has unresolved unknown mechanics: {_format_list(product.unknown_mechanics)}.",
            recommendation="Either map these into the TraderFactory vocabulary or keep them as explicit review blockers.",
            evidence={"unknown_mechanics": list(product.unknown_mechanics)},
        )
    if product.open_questions:
        _finding(
            findings,
            code="product.open_questions",
            severity="warning",
            message=f"{product.symbol} records open questions: {_format_list(product.open_questions)}.",
            recommendation="Resolve the open questions before treating optimization results as meaningful.",
            evidence={"open_questions": list(product.open_questions)},
        )
    if product.special_rules:
        _finding(
            findings,
            code="product.special_rules",
            severity="info",
            message=f"{product.symbol} has product-specific special rules: {_format_list(product.special_rules)}.",
            recommendation="Translate any pricing or execution consequences into typed schema fields where possible.",
            evidence={"special_rules": list(product.special_rules)},
        )

    seen_observation_keys: set[str] = set()
    for channel in product.observation_channels:
        if channel.key in seen_observation_keys:
            _finding(
                findings,
                code="product.duplicate_observation_key",
                severity="warning",
                message=f"{product.symbol} declares the observation key `{channel.key}` more than once.",
                recommendation="Keep observation keys unique so signal routing is unambiguous.",
                evidence={"observation_key": channel.key},
            )
        seen_observation_keys.add(channel.key)
        if channel.source_product and channel.source_product not in declared_symbols:
            _finding(
                findings,
                code="product.observation_unknown_source_product",
                severity="warning",
                message=f"{product.symbol} observation channel `{channel.key}` references undeclared source product `{channel.source_product}`.",
                recommendation="Confirm the source product name or add the missing product to the spec if it is tradable in-round.",
                evidence={"observation_key": channel.key, "source_product": channel.source_product},
            )
        if channel.open_questions:
            _finding(
                findings,
                code="product.observation_open_questions",
                severity="warning",
                message=f"{product.symbol} observation channel `{channel.key}` still has open questions: {_format_list(channel.open_questions)}.",
                recommendation="Resolve the channel semantics before relying on it in generated logic.",
                evidence={"observation_key": channel.key, "open_questions": list(channel.open_questions)},
            )

    basket_required = bool(product.basket_definition is not None or mechanics & BASKET_MECHANICS)
    if basket_required:
        basket = product.basket_definition
        if basket is None:
            _finding(
                findings,
                code="product.basket_missing_definition",
                severity="error",
                message=f"{product.symbol} is basket-like but has no `basket_definition`.",
                recommendation="Provide explicit basket components, weights, and optional divisor/fair offset.",
            )
        else:
            if not basket.components:
                _finding(
                    findings,
                    code="product.basket_missing_components",
                    severity="error",
                    message=f"{product.symbol} has a basket definition without components.",
                    recommendation="Add component symbols and weights before generating basket logic.",
                )
            elif len(basket.components) == 1:
                _finding(
                    findings,
                    code="product.basket_single_component",
                    severity="warning",
                    message=f"{product.symbol} basket definition only contains one component.",
                    recommendation="Confirm that the product is truly basket-based and not better modeled as a spread or direct link.",
                    evidence={"components": [component.symbol for component in basket.components]},
                )
            for component in basket.components:
                if not component.symbol:
                    _finding(
                        findings,
                        code="product.basket_blank_component",
                        severity="error",
                        message=f"{product.symbol} basket definition contains a blank component symbol.",
                        recommendation="Each basket component needs a concrete symbol.",
                    )
                elif component.symbol not in declared_symbols:
                    _finding(
                        findings,
                        code="product.basket_unknown_component",
                        severity="warning",
                        message=f"{product.symbol} basket component `{component.symbol}` is not a declared product in the spec.",
                        recommendation="Confirm whether the component should be another traded product or a nontradable reference feed.",
                        evidence={"component": component.symbol},
                    )
                if component.weight == 0.0:
                    _finding(
                        findings,
                        code="product.basket_zero_weight_component",
                        severity="warning",
                        message=f"{product.symbol} basket component `{component.symbol}` has zero weight.",
                        recommendation="Drop zero-weight components or confirm they are intentional placeholders.",
                        evidence={"component": component.symbol},
                    )
            if basket.divisor is not None and basket.divisor <= 0:
                _finding(
                    findings,
                    code="product.basket_invalid_divisor",
                    severity="error",
                    message=f"{product.symbol} basket divisor must be positive when provided; got {basket.divisor}.",
                    recommendation="Set `basket_definition.divisor` to a positive number or omit it.",
                    evidence={"divisor": basket.divisor},
                )

    derivative_required = bool(product.derivative_contract is not None or mechanics & DERIVATIVE_MECHANICS)
    if derivative_required:
        contract = product.derivative_contract
        if contract is None:
            _finding(
                findings,
                code="product.derivative_missing_contract",
                severity="error",
                message=f"{product.symbol} is derivative-like but has no `derivative_contract`.",
                recommendation="Provide derivative inputs explicitly instead of relying on generic mechanics alone.",
            )
        else:
            if not contract.underlying:
                _finding(
                    findings,
                    code="product.derivative_missing_underlying",
                    severity="error",
                    message=f"{product.symbol} derivative contract does not declare an underlying symbol.",
                    recommendation="Set `derivative_contract.underlying` explicitly.",
                )
            elif contract.underlying not in declared_symbols:
                _finding(
                    findings,
                    code="product.derivative_underlying_not_declared",
                    severity="warning",
                    message=f"{product.symbol} underlying `{contract.underlying}` is not a declared product in the spec.",
                    recommendation="Confirm whether the underlying is a traded product in-round or an external reference.",
                    evidence={"underlying": contract.underlying},
                )
            if contract.option_kind and contract.option_kind not in {"call", "put"}:
                _finding(
                    findings,
                    code="product.derivative_unknown_option_kind",
                    severity="warning",
                    message=f"{product.symbol} option kind `{contract.option_kind}` is not one of `call` or `put`.",
                    recommendation="Use a recognized option kind or keep the product on a deliberate manual-design path.",
                    evidence={"option_kind": contract.option_kind},
                )
            if mechanics & {"option", "expiry"} and not contract.option_kind:
                _finding(
                    findings,
                    code="product.derivative_missing_option_kind",
                    severity="error",
                    message=f"{product.symbol} option mechanics are present but `derivative_contract.option_kind` is missing.",
                    recommendation="Declare whether the contract is a call or put.",
                )
            if contract.strike is None:
                _finding(
                    findings,
                    code="product.derivative_missing_strike",
                    severity="error",
                    message=f"{product.symbol} derivative contract is missing a strike.",
                    recommendation="Set `derivative_contract.strike` explicitly.",
                )
            if contract.time_to_expiry_years is None:
                _finding(
                    findings,
                    code="product.derivative_missing_expiry",
                    severity="error",
                    message=f"{product.symbol} derivative contract is missing time to expiry.",
                    recommendation="Set `time_to_expiry_years` or the equivalent typed expiry field.",
                )
            elif contract.time_to_expiry_years < 0:
                _finding(
                    findings,
                    code="product.derivative_negative_expiry",
                    severity="error",
                    message=f"{product.symbol} derivative contract has negative time to expiry: {contract.time_to_expiry_years}.",
                    recommendation="Use a nonnegative expiry horizon.",
                    evidence={"time_to_expiry_years": contract.time_to_expiry_years},
                )
            if contract.volatility is None:
                _finding(
                    findings,
                    code="product.derivative_missing_volatility",
                    severity="error",
                    message=f"{product.symbol} derivative contract is missing volatility.",
                    recommendation="Provide a volatility convention or keep the product on a deliberate manual-design path.",
                )
            elif contract.volatility < 0:
                _finding(
                    findings,
                    code="product.derivative_negative_volatility",
                    severity="error",
                    message=f"{product.symbol} derivative contract has negative volatility: {contract.volatility}.",
                    recommendation="Use a nonnegative volatility input.",
                    evidence={"volatility": contract.volatility},
                )
            if contract.contract_size is not None and contract.contract_size <= 0:
                _finding(
                    findings,
                    code="product.derivative_invalid_contract_size",
                    severity="error",
                    message=f"{product.symbol} derivative contract size must be positive when provided; got {contract.contract_size}.",
                    recommendation="Set a positive `contract_size` or omit it.",
                    evidence={"contract_size": contract.contract_size},
                )
            if "settlement_formula" in mechanics and not contract.settlement_formula:
                _finding(
                    findings,
                    code="product.derivative_missing_settlement_formula",
                    severity="warning",
                    message=f"{product.symbol} declares settlement-formula mechanics but no settlement formula is recorded.",
                    recommendation="Document the settlement formula explicitly before relying on automated pricing logic.",
                )

    conversion_required = bool(product.conversion_rule is not None or mechanics & CONVERSION_MECHANICS)
    if conversion_required:
        rule = product.conversion_rule
        if rule is None:
            _finding(
                findings,
                code="product.conversion_missing_rule",
                severity="error",
                message=f"{product.symbol} has conversion-related mechanics but no `conversion_rule`.",
                recommendation="Record conversion ratio, fees, delays, and any source or target products explicitly.",
            )
        else:
            if rule.ratio is None:
                _finding(
                    findings,
                    code="product.conversion_missing_ratio",
                    severity="error",
                    message=f"{product.symbol} conversion rule is missing a ratio.",
                    recommendation="Set `conversion_rule.ratio` explicitly.",
                )
            elif rule.ratio <= 0:
                _finding(
                    findings,
                    code="product.conversion_invalid_ratio",
                    severity="error",
                    message=f"{product.symbol} conversion ratio must be positive; got {rule.ratio}.",
                    recommendation="Set a positive conversion ratio.",
                    evidence={"ratio": rule.ratio},
                )
            if rule.delay_steps is not None and rule.delay_steps < 0:
                _finding(
                    findings,
                    code="product.conversion_negative_delay",
                    severity="error",
                    message=f"{product.symbol} conversion delay must be nonnegative; got {rule.delay_steps}.",
                    recommendation="Use a nonnegative `delay_steps` value.",
                    evidence={"delay_steps": rule.delay_steps},
                )
            if rule.lot_size is not None and rule.lot_size <= 0:
                _finding(
                    findings,
                    code="product.conversion_invalid_lot_size",
                    severity="error",
                    message=f"{product.symbol} conversion lot size must be positive; got {rule.lot_size}.",
                    recommendation="Use a positive `lot_size` or omit it if not fixed.",
                    evidence={"lot_size": rule.lot_size},
                )
            if rule.price_observation_key and rule.price_observation_key not in observation_keys:
                _finding(
                    findings,
                    code="product.conversion_unknown_price_observation",
                    severity="warning",
                    message=f"{product.symbol} conversion price observation key `{rule.price_observation_key}` is not declared on the product.",
                    recommendation="Add the observation channel or correct the key before using it as a pricing anchor.",
                    evidence={"price_observation_key": rule.price_observation_key},
                )
            for field_name, field_value in (("source_product", rule.source_product), ("target_product", rule.target_product)):
                if field_value and field_value not in declared_symbols:
                    _finding(
                        findings,
                        code=f"product.conversion_{field_name}_not_declared",
                        severity="warning",
                        message=f"{product.symbol} conversion {field_name} `{field_value}` is not a declared product in the spec.",
                        recommendation="Confirm whether the reference should be another traded product or an external venue leg.",
                        evidence={field_name: field_value},
                    )

    auction_required = bool(product.auction_rule is not None or mechanics & AUCTION_MECHANICS)
    if auction_required:
        rule = product.auction_rule
        if rule is None:
            _finding(
                findings,
                code="product.auction_missing_rule",
                severity="error",
                message=f"{product.symbol} declares auction mechanics but no `auction_rule`.",
                recommendation="Capture the auction schedule, clearing rule, and visibility explicitly.",
            )
        else:
            if not rule.schedule:
                _finding(
                    findings,
                    code="product.auction_missing_schedule",
                    severity="error",
                    message=f"{product.symbol} auction rule is missing a schedule.",
                    recommendation="Set `auction_rule.schedule` explicitly.",
                )
            if not rule.clearing_rule:
                _finding(
                    findings,
                    code="product.auction_missing_clearing_rule",
                    severity="error",
                    message=f"{product.symbol} auction rule is missing a clearing rule.",
                    recommendation="Set `auction_rule.clearing_rule` explicitly.",
                )
            if rule.prep_window is not None and rule.prep_window < 0:
                _finding(
                    findings,
                    code="product.auction_negative_prep_window",
                    severity="error",
                    message=f"{product.symbol} auction prep window must be nonnegative; got {rule.prep_window}.",
                    recommendation="Use a nonnegative `prep_window` value.",
                    evidence={"prep_window": rule.prep_window},
                )
            if rule.submission_window is not None and rule.submission_window < 0:
                _finding(
                    findings,
                    code="product.auction_negative_submission_window",
                    severity="error",
                    message=f"{product.symbol} auction submission window must be nonnegative; got {rule.submission_window}.",
                    recommendation="Use a nonnegative `submission_window` value.",
                    evidence={"submission_window": rule.submission_window},
                )

    participant_required = bool(product.participant_rule is not None or mechanics & PARTICIPANT_MECHANICS)
    if participant_required:
        rule = product.participant_rule
        if rule is None:
            _finding(
                findings,
                code="product.participant_missing_rule",
                severity="error",
                message=f"{product.symbol} has participant-driven mechanics but no `participant_rule`.",
                recommendation="Record tracked participants and how their flow should be interpreted.",
            )
        else:
            if not rule.tracked_participants:
                _finding(
                    findings,
                    code="product.participant_missing_tracked_participants",
                    severity="error",
                    message=f"{product.symbol} participant rule does not declare tracked participants.",
                    recommendation="Populate `tracked_participants` before enabling participant-following logic.",
                )
            if rule.follow_mode and rule.follow_mode not in {"follow", "fade", "gate"}:
                _finding(
                    findings,
                    code="product.participant_unknown_follow_mode",
                    severity="warning",
                    message=f"{product.symbol} participant rule uses unknown follow mode `{rule.follow_mode}`.",
                    recommendation="Use `follow`, `fade`, or `gate`, or document the custom meaning in the surrounding workflow.",
                    evidence={"follow_mode": rule.follow_mode},
                )
            elif not rule.follow_mode:
                _finding(
                    findings,
                    code="product.participant_missing_follow_mode",
                    severity="warning",
                    message=f"{product.symbol} participant rule does not declare a follow mode.",
                    recommendation="Specify whether the sleeve should follow, fade, or gate on participant flow.",
                )
            if rule.signal_horizon is not None and rule.signal_horizon < 0:
                _finding(
                    findings,
                    code="product.participant_negative_signal_horizon",
                    severity="error",
                    message=f"{product.symbol} participant signal horizon must be nonnegative; got {rule.signal_horizon}.",
                    recommendation="Use a nonnegative `signal_horizon` value.",
                    evidence={"signal_horizon": rule.signal_horizon},
                )

    signal_required = bool(product.signal_rule is not None or mechanics & SIGNAL_MECHANICS or signal_candidates)
    if signal_required:
        rule = product.signal_rule
        if rule is None and mechanics & SIGNAL_MECHANICS:
            _finding(
                findings,
                code="product.signal_missing_rule",
                severity="error",
                message=f"{product.symbol} declares signal-driven mechanics but no `signal_rule`.",
                recommendation="Declare the signal source, latency expectations, and staleness policy explicitly.",
            )
        elif rule is None and signal_candidates:
            _finding(
                findings,
                code="product.signal_missing_rule_inferred_channel",
                severity="warning",
                message=f"{product.symbol} has signal-tagged observation channels but no explicit `signal_rule`.",
                recommendation="Add `signal_rule` so the source and staleness policy are explicit rather than inferred.",
                evidence={"signal_candidates": list(signal_candidates)},
            )
        elif rule is not None:
            if not rule.source_key:
                severity = "warning"
                if mechanics & SIGNAL_MECHANICS and len(signal_candidates) != 1 and len(plain_candidates) != 1:
                    severity = "error"
                _finding(
                    findings,
                    code="product.signal_missing_source_key",
                    severity=severity,
                    message=f"{product.symbol} signal rule does not declare a source key.",
                    recommendation="Set `signal_rule.source_key` explicitly, especially when more than one candidate observation exists.",
                    evidence={"signal_candidates": list(signal_candidates), "plain_candidates": list(plain_candidates)},
                )
            elif rule.source_key not in observation_keys:
                _finding(
                    findings,
                    code="product.signal_unknown_source_key",
                    severity="warning",
                    message=f"{product.symbol} signal source key `{rule.source_key}` is not declared on the product.",
                    recommendation="Add the matching observation channel or correct the key.",
                    evidence={"source_key": rule.source_key},
                )
            if rule.staleness_limit is not None and rule.staleness_limit < 0:
                _finding(
                    findings,
                    code="product.signal_negative_staleness_limit",
                    severity="error",
                    message=f"{product.symbol} signal staleness limit must be nonnegative; got {rule.staleness_limit}.",
                    recommendation="Use a nonnegative `staleness_limit` value.",
                    evidence={"staleness_limit": rule.staleness_limit},
                )

    for schema_name, keys in _legacy_schema_usage(product):
        _finding(
            findings,
            code="product.legacy_custom_fields",
            severity="info",
            message=f"{product.symbol} still carries {schema_name} inputs inside `custom_fields`: {_format_list(keys)}.",
            recommendation=f"Move these fields into the typed `{schema_name}` block so the spec remains explicit and easier to validate.",
            evidence={"schema": schema_name, "keys": list(keys)},
        )

    return ProductValidationReport(
        symbol=product.symbol,
        preferred_archetype=interpretation.preferred_archetype,
        fallback_mode=interpretation.fallback_mode,
        findings=_sorted_findings(findings),
    )


def validate_competition_spec(spec: CompetitionSpec) -> CompetitionValidationReport:
    round_findings: list[ValidationFinding] = []
    declared_symbols = [product.symbol for product in spec.products]
    declared_symbol_set = set(declared_symbols)

    if not spec.products:
        _finding(
            round_findings,
            code="round.no_products",
            severity="error",
            message="The competition spec does not declare any products.",
            recommendation="Add at least one product before scaffolding a trader project.",
        )
    duplicate_symbols = sorted({symbol for symbol in declared_symbols if declared_symbols.count(symbol) > 1})
    if duplicate_symbols:
        _finding(
            round_findings,
            code="round.duplicate_product_symbol",
            severity="error",
            message=f"Duplicate product symbols are present: {_format_list(duplicate_symbols)}.",
            recommendation="Keep product symbols unique so generated metadata, params, and project code stay unambiguous.",
            evidence={"duplicate_symbols": duplicate_symbols},
        )
    if spec.unknown_mechanics:
        _finding(
            round_findings,
            code="round.unknown_mechanics",
            severity="warning",
            message=f"Round-level unknown mechanics remain unresolved: {_format_list(spec.unknown_mechanics)}.",
            recommendation="Resolve these before treating generated projects as structurally complete.",
            evidence={"unknown_mechanics": list(spec.unknown_mechanics)},
        )
    if spec.open_questions:
        _finding(
            round_findings,
            code="round.open_questions",
            severity="warning",
            message=f"Round-level open questions remain: {_format_list(spec.open_questions)}.",
            recommendation="Answer these before using optimization results as promotion signals.",
            evidence={"open_questions": list(spec.open_questions)},
        )
    if spec.special_rules:
        _finding(
            round_findings,
            code="round.special_rules",
            severity="info",
            message=f"Round-level special rules are recorded: {_format_list([rule.name or rule.description for rule in spec.special_rules])}.",
            recommendation="Translate any rule that changes pricing, settlement, or execution into machine-readable fields where possible.",
        )
    for relationship in spec.relationships:
        if relationship.left and relationship.left not in declared_symbol_set:
            _finding(
                round_findings,
                code="round.relationship_unknown_left",
                severity="error",
                message=f"Relationship `{relationship.relationship}` references undeclared left product `{relationship.left}`.",
                recommendation="Either add the missing product or remove the invalid relationship entry.",
                evidence={"left": relationship.left, "relationship": relationship.relationship},
            )
        if relationship.right and relationship.right not in declared_symbol_set:
            _finding(
                round_findings,
                code="round.relationship_unknown_right",
                severity="error",
                message=f"Relationship `{relationship.relationship}` references undeclared right product `{relationship.right}`.",
                recommendation="Either add the missing product or remove the invalid relationship entry.",
                evidence={"right": relationship.right, "relationship": relationship.relationship},
            )

    product_reports = [
        _validate_product(product, spec, declared_symbols=declared_symbol_set)
        for product in spec.products
    ]
    return CompetitionValidationReport(
        competition_name=spec.name,
        round_name=spec.round_name,
        round_findings=_sorted_findings(round_findings),
        product_reports=product_reports,
    )


def render_validation_markdown(report: CompetitionValidationReport) -> str:
    counts = report.counts_by_severity()
    product_status_counts = report.product_status_counts()
    lines = [
        f"# Spec Validation: {report.competition_name} / {report.round_name}",
        "",
        "## Summary",
        "",
        f"- Errors: {counts['error']}",
        f"- Warnings: {counts['warning']}",
        f"- Infos: {counts['info']}",
        f"- Products blocked: {product_status_counts['blocked']}",
        f"- Products needing review: {product_status_counts['needs_review']}",
        f"- Products ready: {product_status_counts['ready']}",
        "",
    ]

    lines.append("## Round-Level Findings")
    lines.append("")
    if report.round_findings:
        for finding in _sorted_findings(report.round_findings):
            lines.append(f"- [{finding.severity}] {finding.message}")
            if finding.recommendation:
                lines.append(f"  Recommendation: {finding.recommendation}")
    else:
        lines.append("- No round-level findings.")
    lines.append("")

    lines.append("## Product Findings")
    for product_report in report.product_reports:
        counts = product_report.counts_by_severity()
        lines.extend(
            [
                "",
                f"### {product_report.symbol}",
                "",
                f"- Status: `{product_report.status}`",
                f"- Generated archetype: `{product_report.preferred_archetype}`",
                f"- Fallback mode: `{product_report.fallback_mode}`",
                f"- Errors: {counts['error']}",
                f"- Warnings: {counts['warning']}",
                f"- Infos: {counts['info']}",
            ]
        )
        if product_report.findings:
            lines.append("- Findings:")
            for finding in _sorted_findings(product_report.findings):
                lines.append(f"  - [{finding.severity}] {finding.message}")
                if finding.recommendation:
                    lines.append(f"    Recommendation: {finding.recommendation}")
        else:
            lines.append("- Findings: none.")
    lines.append("")
    return "\n".join(lines)
