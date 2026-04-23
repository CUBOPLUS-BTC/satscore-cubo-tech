"""Data export module for the Magma app.

Provides CSV, JSON, and HTML report generation for user deposits,
savings summaries, remittance comparisons, and pension projections.
"""

from .exporter import DataExporter
from .formatters import CSVFormatter, JSONFormatter, HTMLFormatter
from . import routes

__all__ = ["DataExporter", "CSVFormatter", "JSONFormatter", "HTMLFormatter", "routes"]
