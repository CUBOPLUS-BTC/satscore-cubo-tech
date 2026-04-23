"""RateLimiter — high-level rate limiting facade for the Magma API.

Wraps :class:`~app.ratelimit.storage.MemoryStorage` and adds:

* Endpoint-profile lookups (auth, api, export, scoring, public).
* Composite key generation (IP + endpoint + optional pubkey).
* Standard ``X-RateLimit-*`` response-header generation.
* Aggregate statistics for the admin/health endpoints.
"""

from __future__ import annotations

import hashlib
import time
from typing import Dict, Optional, Tuple

from .storage import MemoryStorage


# ---------------------------------------------------------------------------
# Pre-defined rate-limit profiles
# (limit, window_seconds)
# ---------------------------------------------------------------------------
RATE_LIMITS: Dict[str, Tuple[int, int]] = {
    "auth":     (5,   60),    # 5 auth attempts per minute
    "api":      (60,  60),    # 60 general API calls per minute
    "export":   (5,   300),   # 5 export operations per 5 minutes
    "scoring":  (10,  60),    # 10 scoring requests per minute
    "public":   (120, 60),    # 120 unauthenticated calls per minute
    "webhook":  (20,  60),    # 20 webhook management calls per minute
    "docs":     (200, 60),    # 200 docs calls per minute (very lenient)
}

# Endpoint prefix → profile name
_ENDPOINT_PROFILE_MAP: Dict[str, str] = {
    "/auth":          "auth",
    "/score":         "scoring",
    "/export":        "export",
    "/webhook":       "webhook",
    "/docs":          "docs",
    "/openapi":       "docs",
    "/analytics":     "api",
    "/preferences":   "api",
    "/savings":       "api",
    "/pension":       "api",
    "/remittance":    "api",
    "/lightning":     "api",
    "/network":       "api",
    "/alerts":        "api",
    "/gamification":  "api",
}


class RateLimiter:
    """Rate limiter with sliding-window semantics and per-profile limits.

    Parameters
    ----------
    storage:
        A :class:`MemoryStorage` (or compatible) instance.
    default_limit:
        Requests allowed per window when no profile matches.
    default_window:
        Window length in seconds used when no profile matches.

    Usage
    -----
    ::

        storage = MemoryStorage()
        limiter = RateLimiter(storage)

        result = limiter.check_request(ip="1.2.3.4", endpoint="/auth/challenge")
        if not result["allowed"]:
            headers = limiter.get_headers(result)
            return {"detail": "Too many requests"}, 429, headers
    """

    def __init__(
        self,
        storage: MemoryStorage,
        default_limit: int = 60,
        default_window: int = 60,
    ) -> None:
        self.storage = storage
        self.default_limit = default_limit
        self.default_window = default_window

    # ------------------------------------------------------------------
    # Key generation
    # ------------------------------------------------------------------

    def get_key(self, ip: str, endpoint: str, pubkey: Optional[str] = None) -> str:
        """Build a rate-limit key from the request context.

        The key includes the normalised endpoint prefix so that
        different endpoints don't share a bucket.  If a *pubkey* is
        supplied it replaces the IP component so that authenticated
        users have independent buckets regardless of their IP address
        (useful for mobile clients that share NAT IPs).

        The result is a short SHA-256 hex prefix to keep keys compact.
        """
        # Normalise to the first two path segments.
        parts = [p for p in endpoint.strip("/").split("/") if p]
        prefix = "/" + "/".join(parts[:2]) if parts else "/"

        subject = pubkey if pubkey else ip
        raw = f"{subject}:{prefix}"
        digest = hashlib.sha256(raw.encode()).hexdigest()[:24]
        return f"rl:{digest}"

    # ------------------------------------------------------------------
    # Profile resolution
    # ------------------------------------------------------------------

    def _get_profile(self, endpoint: str) -> str:
        """Return the rate-limit profile name for *endpoint*."""
        endpoint = endpoint.split("?")[0]  # strip query string
        for prefix, profile in _ENDPOINT_PROFILE_MAP.items():
            if endpoint.startswith(prefix):
                return profile
        return "public"

    def _get_limits(
        self,
        endpoint: str,
        limit: Optional[int],
        window: Optional[int],
    ) -> Tuple[int, int]:
        """Resolve effective (limit, window) for a request."""
        if limit is not None and window is not None:
            return limit, window
        profile = self._get_profile(endpoint)
        p_limit, p_window = RATE_LIMITS.get(profile, (self.default_limit, self.default_window))
        return (limit if limit is not None else p_limit,
                window if window is not None else p_window)

    # ------------------------------------------------------------------
    # Core check
    # ------------------------------------------------------------------

    def check(
        self,
        key: str,
        limit: Optional[int] = None,
        window: Optional[int] = None,
    ) -> dict:
        """Check and record a single rate-limit tick for *key*.

        Parameters
        ----------
        key:
            Pre-built rate-limit key (from :meth:`get_key`).
        limit:
            Override the default max requests.
        window:
            Override the default window in seconds.

        Returns
        -------
        dict
            ``{allowed, remaining, reset_at, retry_after}``
        """
        eff_limit = limit if limit is not None else self.default_limit
        eff_window = window if window is not None else self.default_window

        # Check explicit block first (no request recorded for blocked keys).
        if self.storage.is_blocked(key):
            retry_after = self.storage.get_block_remaining(key)
            _, reset_at = self.storage.get_remaining(key, eff_window, eff_limit)
            return {
                "allowed": False,
                "remaining": 0,
                "reset_at": reset_at,
                "retry_after": retry_after,
                "reason": "blocked",
            }

        count = self.storage.record_request(key, eff_window)
        remaining, reset_at = self.storage.get_remaining(key, eff_window, eff_limit)

        if count > eff_limit:
            retry_after = reset_at - int(time.time())
            return {
                "allowed": False,
                "remaining": 0,
                "reset_at": reset_at,
                "retry_after": max(1, retry_after),
                "reason": "rate_limited",
            }

        return {
            "allowed": True,
            "remaining": remaining,
            "reset_at": reset_at,
            "retry_after": None,
            "reason": None,
        }

    # ------------------------------------------------------------------
    # High-level helper
    # ------------------------------------------------------------------

    def check_request(
        self,
        ip: str,
        endpoint: str,
        pubkey: Optional[str] = None,
        limit: Optional[int] = None,
        window: Optional[int] = None,
    ) -> dict:
        """Full request check: build key, resolve profile, call :meth:`check`.

        This is the primary method called by HTTP handlers.

        Parameters
        ----------
        ip:
            Remote address of the client.
        endpoint:
            Request path (e.g. ``/auth/challenge``).
        pubkey:
            Authenticated Nostr pubkey, if available.
        limit / window:
            Optional overrides; if not given, the endpoint profile is used.

        Returns
        -------
        dict
            Same as :meth:`check`.
        """
        eff_limit, eff_window = self._get_limits(endpoint, limit, window)
        key = self.get_key(ip, endpoint, pubkey)
        result = self.check(key, eff_limit, eff_window)
        result["profile"] = self._get_profile(endpoint)
        result["limit"] = eff_limit
        result["window"] = eff_window
        return result

    # ------------------------------------------------------------------
    # Response headers
    # ------------------------------------------------------------------

    def get_headers(self, result: dict) -> dict:
        """Build standard ``X-RateLimit-*`` headers from a check result.

        Returns a plain dict of header name → value strings.
        """
        headers: dict = {
            "X-RateLimit-Limit":     str(result.get("limit", self.default_limit)),
            "X-RateLimit-Remaining": str(result.get("remaining", 0)),
            "X-RateLimit-Reset":     str(result.get("reset_at", 0)),
            "X-RateLimit-Window":    str(result.get("window", self.default_window)),
        }
        if result.get("retry_after") is not None:
            headers["Retry-After"] = str(result["retry_after"])
        if result.get("profile"):
            headers["X-RateLimit-Profile"] = result["profile"]
        return headers

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Return aggregate rate-limit statistics.

        Merges storage-level stats with profile configuration so the
        admin/health endpoint can expose meaningful numbers.
        """
        storage_stats = self.storage.get_stats()
        return {
            "storage": storage_stats,
            "profiles": {
                name: {"limit": lim, "window": win}
                for name, (lim, win) in RATE_LIMITS.items()
            },
            "defaults": {
                "limit": self.default_limit,
                "window": self.default_window,
            },
            "timestamp": int(time.time()),
        }

    # ------------------------------------------------------------------
    # Admin helpers
    # ------------------------------------------------------------------

    def block_ip(self, ip: str, duration: int = 3600) -> None:
        """Block all requests from *ip* for *duration* seconds."""
        # Block across every profile prefix to ensure full coverage.
        for prefix in _ENDPOINT_PROFILE_MAP:
            key = self.get_key(ip, prefix)
            self.storage.block(key, duration)

    def reset_ip(self, ip: str) -> None:
        """Clear all rate-limit state for *ip* (admin action)."""
        for prefix in _ENDPOINT_PROFILE_MAP:
            key = self.get_key(ip, prefix)
            self.storage.reset_key(key)

    def cleanup(self) -> int:
        """Delegate to storage cleanup; returns number of entries removed."""
        return self.storage.cleanup()
