from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _normalize_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key).strip(): raw for key, raw in value.items()}


def _normalize_optional_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_observation_kind(value: Any) -> str:
    kind = _normalize_optional_text(value).lower()
    return kind or "plain"


def _normalize_optional_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    return float(value)


def _normalize_optional_int(value: Any) -> int | None:
    parsed = _normalize_optional_float(value)
    if parsed is None:
        return None
    return int(parsed)


def _normalize_float_mapping(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, float] = {}
    for key, raw in value.items():
        name = str(key).strip()
        if not name:
            continue
        try:
            normalized[name] = float(raw)
        except (TypeError, ValueError):
            continue
    return normalized


@dataclass(slots=True)
class MechanicSpec:
    name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MechanicSpec":
        return cls(
            name=str(data["name"]).strip(),
            description=str(data.get("description", "")).strip(),
            tags=_normalize_list(data.get("tags")),
        )


@dataclass(slots=True)
class ProductRelationshipSpec:
    left: str
    right: str
    relationship: str
    description: str = ""
    hedge_ratio: float | None = None
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProductRelationshipSpec":
        raw_ratio = data.get("hedge_ratio")
        hedge_ratio = None if raw_ratio in {None, ""} else float(raw_ratio)
        return cls(
            left=str(data.get("left", data.get("source", ""))).strip(),
            right=str(data.get("right", data.get("target", ""))).strip(),
            relationship=str(data.get("relationship", data.get("type", ""))).strip(),
            description=str(data.get("description", "")).strip(),
            hedge_ratio=hedge_ratio,
            tags=_normalize_list(data.get("tags")),
        )

    def involves(self, symbol: str) -> bool:
        return symbol in {self.left, self.right}

    def counterpart(self, symbol: str) -> str | None:
        if symbol == self.left:
            return self.right or None
        if symbol == self.right:
            return self.left or None
        return None


@dataclass(slots=True)
class SpecialRuleSpec:
    name: str
    description: str = ""
    scope: str = "round"
    applies_to: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)

    @classmethod
    def from_value(cls, value: Any) -> "SpecialRuleSpec":
        if isinstance(value, dict):
            return cls(
                name=str(value.get("name", "")).strip(),
                description=str(value.get("description", "")).strip(),
                scope=str(value.get("scope", "round")).strip(),
                applies_to=_normalize_list(value.get("applies_to")),
                tags=_normalize_list(value.get("tags")),
                open_questions=_normalize_list(value.get("open_questions")),
            )
        name = str(value).strip()
        return cls(name=name, description=name)


@dataclass(slots=True)
class ObservationChannelSpec:
    key: str
    kind: str = "plain"
    role: str = ""
    description: str = ""
    source_product: str = ""
    units: str = ""
    latency_hint: str = ""
    fields: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    custom_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: Any) -> "ObservationChannelSpec":
        if isinstance(value, dict):
            key = _normalize_optional_text(
                value.get("key")
                or value.get("name")
                or value.get("product")
                or value.get("symbol")
                or value.get("source")
            )
            return cls(
                key=key,
                kind=_normalize_observation_kind(value.get("kind")),
                role=_normalize_optional_text(value.get("role")),
                description=_normalize_optional_text(value.get("description")),
                source_product=_normalize_optional_text(value.get("source_product") or value.get("product")),
                units=_normalize_optional_text(value.get("units")),
                latency_hint=_normalize_optional_text(value.get("latency_hint") or value.get("latency")),
                fields=_normalize_list(value.get("fields")),
                tags=_normalize_list(value.get("tags")),
                open_questions=_normalize_list(value.get("open_questions")),
                custom_fields=_normalize_mapping(value.get("custom_fields")),
            )
        return cls(key=str(value).strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "kind": self.kind,
            "role": self.role,
            "description": self.description,
            "source_product": self.source_product,
            "units": self.units,
            "latency_hint": self.latency_hint,
            "fields": list(self.fields),
            "tags": list(self.tags),
            "open_questions": list(self.open_questions),
            "custom_fields": dict(self.custom_fields),
        }


@dataclass(slots=True)
class DerivativeContractSpec:
    underlying: str = ""
    option_kind: str = ""
    strike: float | None = None
    time_to_expiry_years: float | None = None
    volatility: float | None = None
    risk_free_rate: float | None = None
    carry_rate: float | None = None
    settlement_formula: str = ""
    expiry_style: str = ""
    contract_size: float | None = None
    custom_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: Any) -> "DerivativeContractSpec":
        if not isinstance(value, dict):
            return cls()
        volatility = _normalize_optional_float(value.get("volatility"))
        if volatility is None:
            volatility = _normalize_optional_float(value.get("implied_volatility"))
        if volatility is None:
            volatility_percent = _normalize_optional_float(value.get("volatility_percent"))
            if volatility_percent is not None:
                volatility = volatility_percent / 100.0
        time_to_expiry_years = _normalize_optional_float(value.get("time_to_expiry_years"))
        if time_to_expiry_years is None:
            time_to_expiry_years = _normalize_optional_float(value.get("expiry_years"))
        if time_to_expiry_years is None:
            expiry_days = _normalize_optional_float(value.get("days_to_expiry"))
            if expiry_days is None:
                expiry_days = _normalize_optional_float(value.get("expiry_days"))
            if expiry_days is None:
                expiry_days = _normalize_optional_float(value.get("time_to_expiry_days"))
            if expiry_days is not None:
                time_to_expiry_years = max(0.0, expiry_days) / 365.0
        carry_rate = _normalize_optional_float(value.get("carry_rate"))
        if carry_rate is None:
            carry_rate = _normalize_optional_float(value.get("dividend_yield"))
        return cls(
            underlying=_normalize_optional_text(value.get("underlying")),
            option_kind=_normalize_optional_text(value.get("option_kind") or value.get("option_type")).lower(),
            strike=_normalize_optional_float(value.get("strike")),
            time_to_expiry_years=time_to_expiry_years,
            volatility=volatility,
            risk_free_rate=_normalize_optional_float(value.get("risk_free_rate")),
            carry_rate=carry_rate,
            settlement_formula=_normalize_optional_text(value.get("settlement_formula")),
            expiry_style=_normalize_optional_text(value.get("expiry_style")),
            contract_size=_normalize_optional_float(value.get("contract_size")),
            custom_fields=_normalize_mapping(value.get("custom_fields")),
        )

    def is_empty(self) -> bool:
        return not any(
            (
                self.underlying,
                self.option_kind,
                self.strike is not None,
                self.time_to_expiry_years is not None,
                self.volatility is not None,
                self.risk_free_rate is not None,
                self.carry_rate is not None,
                self.settlement_formula,
                self.expiry_style,
                self.contract_size is not None,
                bool(self.custom_fields),
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "underlying": self.underlying,
            "option_kind": self.option_kind,
            "strike": self.strike,
            "time_to_expiry_years": self.time_to_expiry_years,
            "volatility": self.volatility,
            "risk_free_rate": self.risk_free_rate,
            "carry_rate": self.carry_rate,
            "settlement_formula": self.settlement_formula,
            "expiry_style": self.expiry_style,
            "contract_size": self.contract_size,
            "custom_fields": dict(self.custom_fields),
        }


@dataclass(slots=True)
class ConversionRuleSpec:
    ratio: float | None = None
    fee: float | None = None
    delay_steps: int | None = None
    lot_size: int | None = None
    source_product: str = ""
    target_product: str = ""
    price_observation_key: str = ""
    custom_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: Any) -> "ConversionRuleSpec":
        if not isinstance(value, dict):
            return cls()
        return cls(
            ratio=_normalize_optional_float(value.get("ratio") if "ratio" in value else value.get("conversion_ratio")),
            fee=_normalize_optional_float(value.get("fee") if "fee" in value else value.get("conversion_fee")),
            delay_steps=_normalize_optional_int(value.get("delay_steps") if "delay_steps" in value else value.get("transport_delay")),
            lot_size=_normalize_optional_int(value.get("lot_size")),
            source_product=_normalize_optional_text(value.get("source_product")),
            target_product=_normalize_optional_text(value.get("target_product") or value.get("target_symbol")),
            price_observation_key=_normalize_optional_text(value.get("price_observation_key") or value.get("observation_key")),
            custom_fields=_normalize_mapping(value.get("custom_fields")),
        )

    def is_empty(self) -> bool:
        return not any(
            (
                self.ratio is not None,
                self.fee is not None,
                self.delay_steps is not None,
                self.lot_size is not None,
                self.source_product,
                self.target_product,
                self.price_observation_key,
                bool(self.custom_fields),
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ratio": self.ratio,
            "fee": self.fee,
            "delay_steps": self.delay_steps,
            "lot_size": self.lot_size,
            "source_product": self.source_product,
            "target_product": self.target_product,
            "price_observation_key": self.price_observation_key,
            "custom_fields": dict(self.custom_fields),
        }


@dataclass(slots=True)
class AuctionRuleSpec:
    schedule: str = ""
    clearing_rule: str = ""
    prep_window: int | None = None
    submission_window: int | None = None
    visibility: list[str] = field(default_factory=list)
    custom_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: Any) -> "AuctionRuleSpec":
        if not isinstance(value, dict):
            return cls()
        return cls(
            schedule=_normalize_optional_text(value.get("schedule") or value.get("auction_schedule")),
            clearing_rule=_normalize_optional_text(value.get("clearing_rule")),
            prep_window=_normalize_optional_int(value.get("prep_window") if "prep_window" in value else value.get("pre_open_window")),
            submission_window=_normalize_optional_int(value.get("submission_window")),
            visibility=_normalize_list(value.get("visibility") or value.get("visible_inputs")),
            custom_fields=_normalize_mapping(value.get("custom_fields")),
        )

    def is_empty(self) -> bool:
        return not any(
            (
                self.schedule,
                self.clearing_rule,
                self.prep_window is not None,
                self.submission_window is not None,
                bool(self.visibility),
                bool(self.custom_fields),
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schedule": self.schedule,
            "clearing_rule": self.clearing_rule,
            "prep_window": self.prep_window,
            "submission_window": self.submission_window,
            "visibility": list(self.visibility),
            "custom_fields": dict(self.custom_fields),
        }


@dataclass(slots=True)
class BasketComponentSpec:
    symbol: str
    weight: float = 1.0
    offset: float = 0.0

    @classmethod
    def from_value(cls, value: Any) -> "BasketComponentSpec":
        if not isinstance(value, dict):
            return cls(symbol="")
        symbol = _normalize_optional_text(value.get("symbol") or value.get("counterpart"))
        weight = _normalize_optional_float(value.get("weight") if "weight" in value else value.get("hedge_ratio"))
        offset = _normalize_optional_float(value.get("offset"))
        return cls(
            symbol=symbol,
            weight=1.0 if weight is None else weight,
            offset=0.0 if offset is None else offset,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "weight": self.weight,
            "offset": self.offset,
        }


@dataclass(slots=True)
class BasketDefinitionSpec:
    components: list[BasketComponentSpec] = field(default_factory=list)
    divisor: float | None = None
    fair_offset: float | None = None
    custom_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: Any) -> "BasketDefinitionSpec":
        if not isinstance(value, dict):
            return cls()
        components = [
            component
            for item in value.get("components", [])
            if (component := BasketComponentSpec.from_value(item)).symbol
        ]
        return cls(
            components=components,
            divisor=_normalize_optional_float(value.get("divisor") if "divisor" in value else value.get("basket_divisor")),
            fair_offset=_normalize_optional_float(value.get("fair_offset")),
            custom_fields=_normalize_mapping(value.get("custom_fields")),
        )

    def is_empty(self) -> bool:
        return not any(
            (
                bool(self.components),
                self.divisor is not None,
                self.fair_offset is not None,
                bool(self.custom_fields),
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "components": [component.to_dict() for component in self.components],
            "divisor": self.divisor,
            "fair_offset": self.fair_offset,
            "custom_fields": dict(self.custom_fields),
        }


@dataclass(slots=True)
class ParticipantRuleSpec:
    tracked_participants: list[str] = field(default_factory=list)
    follow_mode: str = ""
    participant_weights: dict[str, float] = field(default_factory=dict)
    signal_horizon: int | None = None
    custom_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: Any) -> "ParticipantRuleSpec":
        if not isinstance(value, dict):
            return cls()
        return cls(
            tracked_participants=_normalize_list(value.get("tracked_participants")),
            follow_mode=_normalize_optional_text(value.get("follow_mode")),
            participant_weights=_normalize_float_mapping(value.get("participant_weights")),
            signal_horizon=_normalize_optional_int(value.get("signal_horizon") if "signal_horizon" in value else value.get("max_signal_age")),
            custom_fields=_normalize_mapping(value.get("custom_fields")),
        )

    def is_empty(self) -> bool:
        return not any(
            (
                bool(self.tracked_participants),
                self.follow_mode,
                bool(self.participant_weights),
                self.signal_horizon is not None,
                bool(self.custom_fields),
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tracked_participants": list(self.tracked_participants),
            "follow_mode": self.follow_mode,
            "participant_weights": dict(self.participant_weights),
            "signal_horizon": self.signal_horizon,
            "custom_fields": dict(self.custom_fields),
        }


@dataclass(slots=True)
class SignalRuleSpec:
    source_key: str = ""
    latency_hint: str = ""
    staleness_limit: int | None = None
    interpretation_mode: str = ""
    custom_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: Any) -> "SignalRuleSpec":
        if not isinstance(value, dict):
            return cls()
        return cls(
            source_key=_normalize_optional_text(value.get("source_key") or value.get("signal_source")),
            latency_hint=_normalize_optional_text(value.get("latency_hint") or value.get("signal_latency")),
            staleness_limit=_normalize_optional_int(value.get("staleness_limit") if "staleness_limit" in value else value.get("max_signal_age")),
            interpretation_mode=_normalize_optional_text(value.get("interpretation_mode") or value.get("mode")),
            custom_fields=_normalize_mapping(value.get("custom_fields")),
        )

    def is_empty(self) -> bool:
        return not any(
            (
                self.source_key,
                self.latency_hint,
                self.staleness_limit is not None,
                self.interpretation_mode,
                bool(self.custom_fields),
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_key": self.source_key,
            "latency_hint": self.latency_hint,
            "staleness_limit": self.staleness_limit,
            "interpretation_mode": self.interpretation_mode,
            "custom_fields": dict(self.custom_fields),
        }


@dataclass(slots=True)
class ProductSpec:
    symbol: str
    position_limit: int
    tick_size: float = 1.0
    price_regime: str = "unknown"
    execution_style: str = "mixed"
    mechanics: list[str] = field(default_factory=list)
    unknown_mechanics: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    observation_channels: list[ObservationChannelSpec] = field(default_factory=list)
    basket_definition: BasketDefinitionSpec | None = None
    participant_rule: ParticipantRuleSpec | None = None
    signal_rule: SignalRuleSpec | None = None
    derivative_contract: DerivativeContractSpec | None = None
    conversion_rule: ConversionRuleSpec | None = None
    auction_rule: AuctionRuleSpec | None = None
    special_rules: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    notes: str = ""
    custom_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProductSpec":
        raw_observations = data.get("observations")
        raw_observation_channels = data.get("observation_channels")
        if raw_observation_channels is None and isinstance(raw_observations, list) and any(
            isinstance(item, dict) for item in raw_observations
        ):
            raw_observation_channels = raw_observations
            raw_observations = [item for item in raw_observations if not isinstance(item, dict)]
        custom_fields = _normalize_mapping(data.get("custom_fields"))
        observation_channels = [
            channel
            for item in (raw_observation_channels or [])
            if (channel := ObservationChannelSpec.from_value(item)).key
        ]
        basket_definition = BasketDefinitionSpec.from_value(data.get("basket_definition") or custom_fields)
        participant_rule = ParticipantRuleSpec.from_value(data.get("participant_rule") or custom_fields)
        signal_rule = SignalRuleSpec.from_value(data.get("signal_rule") or custom_fields)
        derivative_contract = DerivativeContractSpec.from_value(data.get("derivative_contract") or custom_fields)
        conversion_rule = ConversionRuleSpec.from_value(data.get("conversion_rule") or custom_fields)
        auction_rule = AuctionRuleSpec.from_value(data.get("auction_rule") or custom_fields)
        return cls(
            symbol=str(data["symbol"]).strip(),
            position_limit=int(data["position_limit"]),
            tick_size=float(data.get("tick_size", 1.0)),
            price_regime=str(data.get("price_regime", "unknown")).strip(),
            execution_style=str(data.get("execution_style", "mixed")).strip(),
            mechanics=_normalize_list(data.get("mechanics")),
            unknown_mechanics=_normalize_list(data.get("unknown_mechanics")),
            observations=_normalize_list(raw_observations),
            observation_channels=observation_channels,
            basket_definition=None if basket_definition.is_empty() else basket_definition,
            participant_rule=None if participant_rule.is_empty() else participant_rule,
            signal_rule=None if signal_rule.is_empty() else signal_rule,
            derivative_contract=None if derivative_contract.is_empty() else derivative_contract,
            conversion_rule=None if conversion_rule.is_empty() else conversion_rule,
            auction_rule=None if auction_rule.is_empty() else auction_rule,
            special_rules=_normalize_list(data.get("special_rules")),
            open_questions=_normalize_list(data.get("open_questions")),
            notes=str(data.get("notes", "")).strip(),
            custom_fields=custom_fields,
        )

    def observation_keys(self, *, kind: str | None = None, role: str | None = None) -> list[str]:
        keys: list[str] = []
        normalized_kind = _normalize_observation_kind(kind) if kind else ""
        normalized_role = _normalize_optional_text(role).lower()
        for channel in self.observation_channels:
            if normalized_kind and channel.kind != normalized_kind:
                continue
            if normalized_role and channel.role.lower() != normalized_role:
                continue
            if channel.key and channel.key not in keys:
                keys.append(channel.key)
        return keys


@dataclass(slots=True)
class CompetitionSpec:
    name: str
    round_name: str
    description: str = ""
    mechanics: list[MechanicSpec] = field(default_factory=list)
    products: list[ProductSpec] = field(default_factory=list)
    relationships: list[ProductRelationshipSpec] = field(default_factory=list)
    special_rules: list[SpecialRuleSpec] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    unknown_mechanics: list[str] = field(default_factory=list)
    research_goals: list[str] = field(default_factory=list)
    custom_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompetitionSpec":
        mechanics = [MechanicSpec.from_dict(item) for item in data.get("mechanics", [])]
        products = [ProductSpec.from_dict(item) for item in data.get("products", [])]
        relationships = [ProductRelationshipSpec.from_dict(item) for item in data.get("relationships", [])]
        special_rules = [SpecialRuleSpec.from_value(item) for item in data.get("special_rules", [])]
        return cls(
            name=str(data["name"]).strip(),
            round_name=str(data.get("round_name", "")).strip(),
            description=str(data.get("description", "")).strip(),
            mechanics=mechanics,
            products=products,
            relationships=relationships,
            special_rules=special_rules,
            constraints=_normalize_list(data.get("constraints")),
            open_questions=_normalize_list(data.get("open_questions")),
            unknown_mechanics=_normalize_list(data.get("unknown_mechanics")),
            research_goals=_normalize_list(data.get("research_goals")),
            custom_fields=_normalize_mapping(data.get("custom_fields")),
        )

    @classmethod
    def from_json(cls, path: str | Path) -> "CompetitionSpec":
        raw = json.loads(Path(path).read_text())
        return cls.from_dict(raw)

    def relationships_for(self, symbol: str) -> list[ProductRelationshipSpec]:
        return [relationship for relationship in self.relationships if relationship.involves(symbol)]
