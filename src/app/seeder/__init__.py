"""
Seeder package for the Magma Bitcoin application.

Provides:
  - DataGenerator   — realistic fake-data generation
  - DatabaseSeeder  — database population
  - DemoDataSeeder  — curated demo dataset
  - Fixtures        — static test data constants
"""

from .generator import DataGenerator
from .seeder import DatabaseSeeder, DemoDataSeeder
from .fixtures import (
    DEMO_USERS,
    SAMPLE_PRICES,
    SAMPLE_DEPOSITS,
    SAMPLE_ACHIEVEMENTS,
    BENCHMARK_DATA,
    COUNTRY_DATA,
    FEE_HISTORY,
    MEMPOOL_SAMPLES,
    LIGHTNING_SAMPLES,
    EXCHANGE_RATES,
    HISTORICAL_HALVINGS,
    NOTABLE_ADDRESSES,
    TEST_VECTORS,
)

__all__ = [
    "DataGenerator",
    "DatabaseSeeder",
    "DemoDataSeeder",
    "DEMO_USERS",
    "SAMPLE_PRICES",
    "SAMPLE_DEPOSITS",
    "SAMPLE_ACHIEVEMENTS",
    "BENCHMARK_DATA",
    "COUNTRY_DATA",
    "FEE_HISTORY",
    "MEMPOOL_SAMPLES",
    "LIGHTNING_SAMPLES",
    "EXCHANGE_RATES",
    "HISTORICAL_HALVINGS",
    "NOTABLE_ADDRESSES",
    "TEST_VECTORS",
]
