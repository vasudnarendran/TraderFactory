"""Core TraderFactory types."""

from trader_factory.core import datamodel
from trader_factory.core.registry import STRATEGY_REGISTRY, StrategyCapability, recommend_capabilities
from trader_factory.core.specs import CompetitionSpec, MechanicSpec, ProductSpec
from trader_factory.core.validation import (
    CompetitionValidationReport,
    ProductValidationReport,
    ValidationFinding,
    render_validation_markdown,
    validate_competition_spec,
)

__all__ = [
    "CompetitionSpec",
    "CompetitionValidationReport",
    "MechanicSpec",
    "ProductValidationReport",
    "ProductSpec",
    "STRATEGY_REGISTRY",
    "StrategyCapability",
    "ValidationFinding",
    "recommend_capabilities",
    "datamodel",
    "render_validation_markdown",
    "validate_competition_spec",
]
