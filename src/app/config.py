"""Runtime configuration.

Reads settings from environment variables (optionally populated via a
local ``.env`` file). Required values are validated lazily — importing
this module never raises, which keeps test collection and lint runs
stable even when the environment isn't fully configured.
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv


load_dotenv()


class MissingConfigError(RuntimeError):
    """Raised when a required configuration value is missing at use time."""


def _require(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise MissingConfigError(f"{name} is not configured")
    return value


class Settings:
    @property
    def DATABASE_URL(self) -> str:
        return _require("DATABASE_URL")

    @property
    def PUBLIC_URL(self) -> str:
        return _require("PUBLIC_URL")

    @property
    def COINGECKO_API_KEY(self) -> str:
        return os.environ.get("COINGECKO_API_KEY", "")

    @property
    def CORS_ORIGINS(self) -> list:
        raw = os.environ.get("CORS_ORIGINS", '["http://localhost:8080"]')
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return ["http://localhost:8080"]
            return parsed if isinstance(parsed, list) else ["http://localhost:8080"]
        return raw


settings = Settings()
