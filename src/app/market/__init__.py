"""Market data engine package for Magma Bitcoin app."""

from .engine import MarketEngine
from .history import PriceHistory, HistoricalEvent, BITCOIN_HISTORICAL_EVENTS
from .orderbook import OrderBook, OrderBookAnalyzer
from .signals import SignalEngine, AlertEngine, Alert

__all__ = [
    "MarketEngine",
    "PriceHistory",
    "HistoricalEvent",
    "BITCOIN_HISTORICAL_EVENTS",
    "OrderBook",
    "OrderBookAnalyzer",
    "SignalEngine",
    "AlertEngine",
    "Alert",
]
