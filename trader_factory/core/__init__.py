"""Core TraderFactory types."""

from trader_factory.core import datamodel
from trader_factory.core.registry import STRATEGY_REGISTRY, StrategyCapability, recommend_capabilities
from trader_factory.core.specs import CompetitionSpec, MechanicSpec, ProductSpec

__all__ = [
    "CompetitionSpec",
    "MechanicSpec",
    "ProductSpec",
    "STRATEGY_REGISTRY",
    "StrategyCapability",
    "recommend_capabilities",
    "datamodel",
]
