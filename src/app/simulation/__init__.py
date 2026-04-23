"""Simulation engine package for Magma Bitcoin app."""

from .montecarlo import MonteCarloEngine
from .backtest import BacktestEngine, Strategy, BacktestResult, Order
from .scenarios import ScenarioAnalyzer, PREDEFINED_SCENARIOS

__all__ = [
    "MonteCarloEngine",
    "BacktestEngine",
    "Strategy",
    "BacktestResult",
    "Order",
    "ScenarioAnalyzer",
    "PREDEFINED_SCENARIOS",
]
