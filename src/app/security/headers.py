"""
Security HTTP headers for Magma Bitcoin app.
Generates all recommended security headers: CSP, HSTS, CORS, Permissions-Policy, etc.
Pure Python stdlib — no third-party dependencies.
"""

import secrets
import re
import urllib.parse
from typing import Optional


# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------

_DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "http://localhost:5173",
    "http://localhost:4173",
]

_DEFAULT_CSP_DIRECTIVES = {
    "default-src":  ["'self'"],
    "script-src":   ["'self'", "'nonce-{nonce}'"],
    "style-src":    ["'self'", "'nonce-{nonce}'", "'unsafe-inline'"],
    "img-src":      ["'self'", "data:", "https://api.coingecko.com"],
    "font-src":     ["'self'", "data:"],
    "connect-src":  [
        "'self'",
        "https://api.coingecko.com",
        "https://mempool.space",
        "wss://relay.damus.io",
        "wss://relay.nostr.band",
        "wss://nos.lol",
    ],
    "frame-src":    ["'none'"],
    "object-src":   ["'none'"],
    "base-uri":     ["'self'"],
    "form-action":  ["'self'"],
    "manifest-src": ["'self'"],
    "worker-src":   ["'self'", "blob:"],
}

_DEFAULT_PERMISSIONS = {
    "accelerometer":        "()",
    "ambient-light-sensor": "()",
    "autoplay":             "()",
    "battery":              "()",
    "camera":               "()",
    "cross-origin-isolated": "()",
    "display-capture":      "()",
    "document-domain":      "()",
    "encrypted-media":      "()",
    "execution-while-not-rendered": "()",
    "execution-while-out-of-viewport": "()",
    "fullscreen":           "(self)",
    "geolocation":          "()",
    "gyroscope":            "()",
    "keyboard-map":         "()",
    "magnetometer":         "()",
    "microphone":           "()",
    "midi":                 "()",
    "navigation-override":  "()",
    "payment":              "()",
    "picture-in-picture":   "()",
    "publickey-credentials-get": "(self)",
    "screen-wake-lock":     "()",
    "sync-xhr":             "()",
    "usb":                  "()",
    "web-share":            "(self)",
    "xr-spatial-tracking":  "()",
}


# ---------------------------------------------------------------------------
# SecurityHeaders
# ---------------------------------------------------------------------------

class SecurityHeaders:
    """
    Centralised security headers manager for the Magma Bitcoin API.

    Provides all OWASP-recommended HTTP security headers with sane defaults
    tailored for a Bitcoin / Nostr application.
    """

    def __init__(
        self,
        allowed_origins: list = None,
        hsts_max_age: int = 31_536_000,
        include_subdomains: bool = True,
        preload_hsts: bool = False,
        csp_report_uri: str = "",
        frame_ancestors: str = "'none'",
    ) -> None:
        self._allowed_origins  = allowed_origins or list(_DEFAULT_ALLOWED_ORIGINS)
        self._hsts_max_age     = hsts_max_age
        self._include_sub      = include_subdomains
        self._preload_hsts     = preload_hsts
        self._csp_report_uri   = csp_report_uri
        self._frame_ancestors  = frame_ancestors

    # ------------------------------------------------------------------
    # Nonce generation
    # ------------------------------------------------------------------

    @staticmethod
    def generate_nonce() -> str:
        """Generate a cryptographically secure random nonce for CSP."""
        return secrets.token_urlsafe(16)

    # ------------------------------------------------------------------
    # Individual header builders
    # ------------------------------------------------------------------

    def get_csp_header(self, nonce: str = "") -> str:
        """
        Build a Content-Security-Policy header value.

        If ``nonce`` is provided it is substituted into script-src and style-src.
        Returns the full CSP header string.
        """
        if not nonce:
            nonce = self.generate_nonce()

        parts = []
        for directive, sources in _DEFAULT_CSP_DIRECTIVES.items():
            resolved = [s.replace("{nonce}", nonce) for s in sources]

            # Add frame-ancestors as a CSP directive
            if directive == "frame-src":
                parts.append(f"frame-ancestors {self._frame_ancestors}")

            parts.append(f"{directive} {' '.join(resolved)}")

        if self._csp_report_uri:
            parts.append(f"report-uri {self._csp_report_uri}")

        return "; ".join(parts)

    def get_hsts_header(self, max_age: int = None) -> str:
        """
        Build the Strict-Transport-Security header value.

        Args:
            max_age: Override the configured max-age (seconds).
        """
        age = max_age if max_age is not None else self._hsts_max_age
        parts = [f"max-age={age}"]

        if self._include_sub:
            parts.append("includeSubDomains")

        if self._preload_hsts:
            parts.append("preload")

        return "; ".join(parts)

    def get_cors_headers(
        self,
        origin: str,
        allowed_origins: list = None,
        allow_credentials: bool = True,
        max_age: int = 86400,
        extra_methods: list = None,
        extra_headers: list = None,
    ) -> dict:
        """
        Build CORS response headers for the given request origin.

        Returns an empty dict if the origin is not allowed.
        """
        origins = allowed_origins or self._allowed_origins

        if not self.validate_origin(origin, origins):
            return {}

        methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
        if extra_methods:
            methods.extend(extra_methods)

        headers_list = [
            "Content-Type", "Authorization", "X-Request-ID",
            "X-Signature", "X-Timestamp",
        ]
        if extra_headers:
            headers_list.extend(extra_headers)

        result = {
            "Access-Control-Allow-Origin":  origin,
            "Access-Control-Allow-Methods": ", ".join(methods),
            "Access-Control-Allow-Headers": ", ".join(headers_list),
            "Access-Control-Max-Age":       str(max_age),
            "Vary":                         "Origin",
        }

        if allow_credentials:
            result["Access-Control-Allow-Credentials"] = "true"

        return result

    def get_permissions_policy(self) -> str:
        """Build the Permissions-Policy header value."""
        parts = [
            f"{feature}={value}"
            for feature, value in _DEFAULT_PERMISSIONS.items()
        ]
        return ", ".join(parts)

    def get_frame_options(self) -> str:
        """Return X-Frame-Options header value."""
        if self._frame_ancestors == "'none'":
            return "DENY"
        if self._frame_ancestors == "'self'":
            return "SAMEORIGIN"
        return "DENY"

    @staticmethod
    def get_content_type_options() -> str:
        """Return X-Content-Type-Options header value."""
        return "nosniff"

    @staticmethod
    def get_xss_protection() -> str:
        """Return X-XSS-Protection header value (legacy browsers)."""
        return "1; mode=block"

    @staticmethod
    def get_referrer_policy() -> str:
        """Return Referrer-Policy header value."""
        return "strict-origin-when-cross-origin"

    @staticmethod
    def get_cross_origin_embedder_policy() -> str:
        return "require-corp"

    @staticmethod
    def get_cross_origin_opener_policy() -> str:
        return "same-origin"

    @staticmethod
    def get_cross_origin_resource_policy() -> str:
        return "same-site"

    # ------------------------------------------------------------------
    # Composite helper
    # ------------------------------------------------------------------

    def get_default_headers(
        self,
        origin: str = "",
        nonce: str = "",
        include_cors: bool = True,
    ) -> dict:
        """
        Return a complete dict of all recommended security headers.
        Suitable for attaching to every HTTP response.

        Args:
            origin:       Request Origin header value (for CORS).
            nonce:        CSP nonce (generated fresh if not provided).
            include_cors: Whether to include CORS headers.
        """
        if not nonce:
            nonce = self.generate_nonce()

        headers: dict = {
            "Content-Security-Policy":       self.get_csp_header(nonce),
            "Strict-Transport-Security":     self.get_hsts_header(),
            "X-Content-Type-Options":        self.get_content_type_options(),
            "X-Frame-Options":               self.get_frame_options(),
            "X-XSS-Protection":              self.get_xss_protection(),
            "Referrer-Policy":               self.get_referrer_policy(),
            "Permissions-Policy":            self.get_permissions_policy(),
            "Cross-Origin-Embedder-Policy":  self.get_cross_origin_embedder_policy(),
            "Cross-Origin-Opener-Policy":    self.get_cross_origin_opener_policy(),
            "Cross-Origin-Resource-Policy":  self.get_cross_origin_resource_policy(),
            "Cache-Control":                 "no-store, no-cache, must-revalidate",
            "Pragma":                        "no-cache",
            "X-Request-ID":                  secrets.token_hex(8),
            "X-Content-Security-Policy":     self.get_csp_header(nonce),  # IE compat
        }

        if include_cors and origin:
            cors = self.get_cors_headers(origin)
            headers.update(cors)

        return headers

    def get_api_headers(self, origin: str = "") -> dict:
        """
        Minimal security headers for JSON API responses.
        Lighter than the full browser-facing header set.
        """
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options":        "DENY",
            "Referrer-Policy":        "no-referrer",
            "Cache-Control":          "no-store",
            "X-Request-ID":           secrets.token_hex(8),
        }

        if origin:
            cors = self.get_cors_headers(origin)
            headers.update(cors)

        return headers

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def validate_origin(self, origin: str, allowed: list = None) -> bool:
        """
        Check whether an Origin header value is in the allowed list.
        Supports exact matches and wildcard subdomain patterns like ``*.example.com``.
        """
        if not origin:
            return False

        origins = allowed or self._allowed_origins

        for allowed_origin in origins:
            if allowed_origin == origin:
                return True

            # Wildcard subdomain support: "https://*.example.com"
            if allowed_origin.startswith("https://*.") or allowed_origin.startswith("http://*."):
                scheme_and_star, domain = allowed_origin.split("*.", 1)
                if origin.startswith(scheme_and_star.replace("*.", "")):
                    origin_domain = re.sub(r"^https?://[^.]+\.", "", origin)
                    if origin_domain == domain:
                        return True

        return False

    def validate_referer(self, referer: str, expected_host: str) -> bool:
        """
        Validate that a Referer header matches the expected host.
        Returns True if the referer belongs to expected_host.
        """
        if not referer or not expected_host:
            return False

        try:
            parsed = urllib.parse.urlparse(referer)
            return parsed.netloc == expected_host or parsed.netloc.endswith(f".{expected_host}")
        except Exception:
            return False

    def add_allowed_origin(self, origin: str) -> None:
        """Add an origin to the allowed list at runtime."""
        if origin and origin not in self._allowed_origins:
            self._allowed_origins.append(origin)

    def remove_allowed_origin(self, origin: str) -> bool:
        """Remove an origin from the allowed list. Returns True if removed."""
        if origin in self._allowed_origins:
            self._allowed_origins.remove(origin)
            return True
        return False

    def get_allowed_origins(self) -> list:
        """Return a copy of the current allowed origins list."""
        return list(self._allowed_origins)

    # ------------------------------------------------------------------
    # Response wrapper helper
    # ------------------------------------------------------------------

    def apply_to_response(
        self,
        response_headers: dict,
        origin: str = "",
        nonce: str = "",
    ) -> dict:
        """
        Merge security headers into an existing response headers dict.
        Returns the updated headers dict.
        """
        security = self.get_default_headers(origin=origin, nonce=nonce)
        response_headers.update(security)
        return response_headers
