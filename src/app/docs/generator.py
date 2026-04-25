"""OpenAPIGenerator — produces an OpenAPI 3.0 specification for Magma.

The generator assembles the full spec from the schema definitions in
``schemas.py`` and the static metadata below.  It produces both JSON
and a human-readable YAML-like text format (without any third-party
dependencies).
"""

from __future__ import annotations

import json
import time
from typing import Any

from .schemas import ENDPOINT_SCHEMAS, COMPONENT_SCHEMAS

# ---------------------------------------------------------------------------
# Static API metadata
# ---------------------------------------------------------------------------

API_TITLE = "Magma Bitcoin API"
API_VERSION = "1.0.0"
API_DESCRIPTION = (
    "Magma is a Bitcoin savings, analytics, and education app built for "
    "El Salvador and emerging markets.  It runs on 100% geothermal energy "
    "and uses Nostr / LNURL for authentication.\n\n"
    "## Authentication\n\n"
    "Most endpoints accept two auth methods:\n\n"
    "* **Bearer token** — obtained via `POST /auth/verify` or LNURL-auth flow.  "
    "Pass as `Authorization: Bearer <token>`.\n"
    "* **Nostr NIP-98** — sign an HTTP-auth event and pass as "
    "`Authorization: Nostr <base64-event>`.\n\n"
    "## Rate Limits\n\n"
    "Standard `X-RateLimit-*` headers are returned on every response.  "
    "Exceeding the limit returns HTTP 429 with a `Retry-After` header.\n\n"
    "| Profile  | Limit | Window |\n"
    "|----------|-------|--------|\n"
    "| auth     | 5     | 60 s   |\n"
    "| api      | 60    | 60 s   |\n"
    "| export   | 5     | 300 s  |\n"
    "| scoring  | 10    | 60 s   |\n"
    "| public   | 120   | 60 s   |\n"
)

CONTACT_INFO = {
    "name": "Magma / CUBO+ Hackathon",
    "url": "https://github.com/wkatir/magma",
    "email": "mgarcia@rivka.mx",
}

LICENSE_INFO = {
    "name": "MIT",
    "url": "https://opensource.org/licenses/MIT",
}

SERVER_LIST = [
    {"url": "https://api.eclalune.com", "description": "Production (Hetzner)"},
    {"url": "http://localhost:8000",    "description": "Local development"},
]


class OpenAPIGenerator:
    """Generate an OpenAPI 3.0.3 specification for the Magma API.

    Usage
    -----
    ::

        gen = OpenAPIGenerator()
        spec_dict = gen.generate()
        json_str  = gen.to_json()
        yaml_str  = gen.to_yaml_like()
    """

    def __init__(
        self,
        title: str = API_TITLE,
        version: str = API_VERSION,
        description: str = API_DESCRIPTION,
    ) -> None:
        self.title = title
        self.version = version
        self.description = description
        self._generated_at: int = 0
        self._spec_cache: dict | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self) -> dict:
        """Assemble and return the full OpenAPI 3.0 spec as a dict."""
        spec = {
            "openapi": "3.0.3",
            "info":    self._build_info(),
            "servers": SERVER_LIST,
            "paths":   self._build_paths(),
            "components": self._build_components(),
            "security":  [{"bearerAuth": []}, {"nostrAuth": []}],
            "tags": self._build_tags(),
            "externalDocs": {
                "description": "Magma GitHub repository",
                "url": "https://github.com/wkatir/magma",
            },
        }
        self._generated_at = int(time.time())
        self._spec_cache = spec
        return spec

    def to_json(self, indent: int = 2) -> str:
        """Serialise the spec to a JSON string."""
        spec = self._spec_cache if self._spec_cache else self.generate()
        return json.dumps(spec, indent=indent, ensure_ascii=False)

    def to_yaml_like(self) -> str:
        """Serialise the spec to a YAML-like text without pyyaml.

        This is intentionally readable rather than 100% spec-compliant
        YAML — it is suitable for human review or copy-paste into an
        online validator but should not be relied on for machine parsing.
        """
        spec = self._spec_cache if self._spec_cache else self.generate()
        return self._dict_to_yaml(spec, indent=0)

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_info(self) -> dict:
        return {
            "title":       self.title,
            "version":     self.version,
            "description": self.description,
            "contact":     CONTACT_INFO,
            "license":     LICENSE_INFO,
            "x-generated-at": self._generated_at or int(time.time()),
        }

    def _build_paths(self) -> dict:
        """Assemble the ``paths`` object from ``ENDPOINT_SCHEMAS``."""
        paths: dict[str, dict] = {}

        for ep in ENDPOINT_SCHEMAS:
            path   = ep["path"]
            method = ep["method"].lower()

            if path not in paths:
                paths[path] = {}

            operation: dict[str, Any] = {
                "summary":     ep.get("summary", ""),
                "description": ep.get("description", ""),
                "tags":        ep.get("tags", []),
                "operationId": self._operation_id(method, path),
                "responses":   ep.get("responses", {}),
            }

            params = ep.get("parameters")
            if params:
                operation["parameters"] = params

            body = ep.get("request_body")
            if body:
                operation["requestBody"] = body

            if ep.get("auth_required"):
                operation["security"] = [{"bearerAuth": []}, {"nostrAuth": []}]
            else:
                operation["security"] = []

            paths[path][method] = operation

        return paths

    def _build_components(self) -> dict:
        return {
            "schemas":         COMPONENT_SCHEMAS,
            "securitySchemes": self._build_security(),
            "responses": {
                "UnauthorizedError": {
                    "description": "Authentication credentials are missing or invalid.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "detail": {"type": "string"},
                                },
                            }
                        }
                    },
                },
                "TooManyRequests": {
                    "description": "Rate limit exceeded.",
                    "headers": {
                        "Retry-After":         {"schema": {"type": "integer"}},
                        "X-RateLimit-Limit":   {"schema": {"type": "integer"}},
                        "X-RateLimit-Remaining":{"schema": {"type": "integer"}},
                        "X-RateLimit-Reset":   {"schema": {"type": "integer"}},
                    },
                },
            },
        }

    def _build_security(self) -> dict:
        return {
            "bearerAuth": {
                "type":         "http",
                "scheme":       "bearer",
                "bearerFormat": "JWT-like opaque token",
                "description":  "Bearer token obtained from /auth/verify or LNURL-auth flow.",
            },
            "nostrAuth": {
                "type":        "apiKey",
                "in":          "header",
                "name":        "Authorization",
                "description": (
                    "Nostr NIP-98 HTTP Auth.  "
                    "Pass ``Authorization: Nostr <base64-encoded-event>`` where the "
                    "event is a kind-27235 Nostr event signed by the user."
                ),
            },
        }

    def _build_tags(self) -> list:
        tag_descriptions = {
            "Authentication": "Nostr and LNURL-auth endpoints for user login and session management.",
            "Scoring":        "Bitcoin address on-chain analysis and scoring.",
            "Preferences":    "User alert preferences and notification thresholds.",
            "Savings":        "DCA savings goals, deposit tracking, and projections.",
            "Pension":        "Long-term Bitcoin accumulation and retirement projections.",
            "Remittance":     "Bitcoin remittance quotes and cost-comparison projections.",
            "Lightning":      "Lightning Network statistics and node information.",
            "Network":        "Bitcoin network health: mempool, fees, and recent blocks.",
            "Analytics":      "User activity analytics and platform-level statistics.",
            "Gamification":   "Achievements, badges, and leaderboard.",
            "Export":         "PDF export for savings, pension, and remittance reports.",
            "Alerts":         "Real-time fee and price alerts.",
            "Webhooks":       "Webhook subscription management and delivery.",
            "Documentation":  "OpenAPI spec and interactive Swagger UI.",
        }
        tags = []
        seen: set[str] = set()
        for ep in ENDPOINT_SCHEMAS:
            for tag in ep.get("tags", []):
                if tag not in seen:
                    seen.add(tag)
                    tags.append({
                        "name":        tag,
                        "description": tag_descriptions.get(tag, ""),
                    })
        return tags

    # ------------------------------------------------------------------
    # YAML-like serialiser
    # ------------------------------------------------------------------

    def _dict_to_yaml(self, obj: Any, indent: int) -> str:
        pad = "  " * indent
        lines: list[str] = []

        if isinstance(obj, dict):
            for key, value in obj.items():
                key_str = self._yaml_key(str(key))
                if isinstance(value, (dict, list)):
                    lines.append(f"{pad}{key_str}:")
                    lines.append(self._dict_to_yaml(value, indent + 1))
                else:
                    lines.append(f"{pad}{key_str}: {self._yaml_scalar(value)}")

        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    first_line = self._dict_to_yaml(item, indent + 1).lstrip()
                    lines.append(f"{pad}- {first_line}")
                    # Remaining lines of this list item (already indented).
                    inner = self._dict_to_yaml(item, indent + 1)
                    inner_lines = inner.split("\n")[1:]
                    lines.extend(inner_lines)
                else:
                    lines.append(f"{pad}- {self._yaml_scalar(item)}")
        else:
            lines.append(f"{pad}{self._yaml_scalar(obj)}")

        return "\n".join(lines)

    @staticmethod
    def _yaml_key(key: str) -> str:
        if any(c in key for c in " :/"):
            return f'"{key}"'
        return key

    @staticmethod
    def _yaml_scalar(value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        text = str(value)
        if "\n" in text:
            return "|-\n" + "\n".join("  " + line for line in text.splitlines())
        if any(c in text for c in ":{[],#&*!|>'\"%@`"):
            return json.dumps(text)
        return text

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _operation_id(method: str, path: str) -> str:
        """Derive a camelCase operationId from method + path."""
        clean = path.replace("/", "_").replace("{", "").replace("}", "").strip("_")
        parts = [p for p in clean.split("_") if p]
        camel = method + "".join(p.capitalize() for p in parts)
        return camel

    def get_endpoint_count(self) -> int:
        return len(ENDPOINT_SCHEMAS)

    def get_tag_list(self) -> list[str]:
        seen: list[str] = []
        for ep in ENDPOINT_SCHEMAS:
            for tag in ep.get("tags", []):
                if tag not in seen:
                    seen.append(tag)
        return seen
