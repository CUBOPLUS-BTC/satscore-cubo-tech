"""Magma SDK — Python client for the SatScore / Magma backend."""

from .async_client import AsyncMagmaClient
from .client import MagmaClient
from .exceptions import (
    APIError,
    AuthenticationError,
    MagmaError,
    NotFoundError,
    PermissionError_,
    RateLimitError,
    ServerError,
    TransportError,
    ValidationError,
)
from .models import (
    Alert,
    PensionProjection,
    PriceQuote,
    ProjectionScenario,
    RemittanceChannel,
    RemittanceComparison,
    SavingsProgress,
    SavingsProjection,
    SendTimeRecommendation,
)
from .resources.auth import AuthSession, Challenge, LnurlChallenge, LnurlStatus


__version__ = "0.2.0"

__all__ = [
    "MagmaClient",
    "AsyncMagmaClient",
    # Errors
    "MagmaError",
    "TransportError",
    "APIError",
    "ValidationError",
    "AuthenticationError",
    "PermissionError_",
    "NotFoundError",
    "RateLimitError",
    "ServerError",
    # Models
    "Alert",
    "PensionProjection",
    "PriceQuote",
    "ProjectionScenario",
    "RemittanceChannel",
    "RemittanceComparison",
    "SavingsProgress",
    "SavingsProjection",
    "SendTimeRecommendation",
    "AuthSession",
    "Challenge",
    "LnurlChallenge",
    "LnurlStatus",
]
