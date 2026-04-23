"""Analytics module for the Magma app.

Provides event tracking, user activity summaries, platform-level
statistics, retention cohort analysis, and feature usage metrics.
"""

from .engine import AnalyticsEngine
from .aggregator import DataAggregator
from . import routes

__all__ = ["AnalyticsEngine", "DataAggregator", "routes"]
