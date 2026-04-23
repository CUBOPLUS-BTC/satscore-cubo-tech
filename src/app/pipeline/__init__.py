"""
Pipeline package - ETL framework, transformers, validators, and processors
for the Magma Bitcoin application.
"""

from .etl import (
    Pipeline,
    PipelineStep,
    PipelineResult,
    DataExtractor,
    DataLoader,
    build_price_update_pipeline,
    build_user_analytics_pipeline,
    build_deposit_aggregation_pipeline,
    build_compliance_check_pipeline,
)
from .transformers import Transformers
from .validators import DataValidator, ValidationResult, SchemaValidator
from .processors import (
    BatchProcessor,
    StreamProcessor,
    AggregationProcessor,
    TimeSeriesProcessor,
)

__all__ = [
    "Pipeline",
    "PipelineStep",
    "PipelineResult",
    "DataExtractor",
    "DataLoader",
    "build_price_update_pipeline",
    "build_user_analytics_pipeline",
    "build_deposit_aggregation_pipeline",
    "build_compliance_check_pipeline",
    "Transformers",
    "DataValidator",
    "ValidationResult",
    "SchemaValidator",
    "BatchProcessor",
    "StreamProcessor",
    "AggregationProcessor",
    "TimeSeriesProcessor",
]
