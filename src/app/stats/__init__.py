"""Bitcoin data statistics module.

Provides a pure-stdlib statistical analysis engine for Bitcoin price series,
on-chain metrics, and other numerical data.  No third-party libraries are used.

Public surface
--------------
Calculator
  - StatisticsCalculator : class

Routes (HTTP handlers, return (body_dict, status_code))
  - handle_stats_analyze()
  - handle_stats_correlation()
  - handle_stats_regression()
"""

from .calculator import StatisticsCalculator
from .routes import (
    handle_stats_analyze,
    handle_stats_correlation,
    handle_stats_regression,
)

__all__ = [
    "StatisticsCalculator",
    "handle_stats_analyze",
    "handle_stats_correlation",
    "handle_stats_regression",
]
