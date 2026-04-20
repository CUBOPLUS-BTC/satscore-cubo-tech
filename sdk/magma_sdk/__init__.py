"""Magma SDK — Python client for the SatScore / Magma backend."""

from ._transport import (
    IDEMPOTENCY_HEADER,
    REQUEST_ID_HEADER,
    RetryEvent,
    generate_request_id,
)
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
    LiquidAsset,
    LiquidNetworkStatus,
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
from .webhooks import (
    InvalidSignatureError,
    MalformedWebhookError,
    ReplayError,
    WebhookError,
    WebhookEvent,
    WebhookVerifier,
    sign as sign_webhook,
)


__version__ = "0.4.0"

__all__ = [
    "MagmaClient",
    "AsyncMagmaClient",
    # Transport
    "RetryEvent",
    "REQUEST_ID_HEADER",
    "IDEMPOTENCY_HEADER",
    "generate_request_id",
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
    "LiquidAsset",
    "LiquidNetworkStatus",
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
    # Webhooks
    "WebhookVerifier",
    "WebhookEvent",
    "WebhookError",
    "InvalidSignatureError",
    "ReplayError",
    "MalformedWebhookError",
    "sign_webhook",
]
