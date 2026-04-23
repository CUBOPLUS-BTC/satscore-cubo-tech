import os
import json
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.environ["DATABASE_URL"]
    PUBLIC_URL: str = os.environ["PUBLIC_URL"]
    COINGECKO_API_KEY: str = os.environ.get("COINGECKO_API_KEY", "")
    DEV_MODE: bool = os.environ.get("DEV_MODE", "false").lower() == "true"

    @property
    def CORS_ORIGINS(self) -> list:
        raw = os.environ.get("CORS_ORIGINS", '["http://localhost:8080"]')
        if isinstance(raw, str):
            return json.loads(raw)
        return raw


settings = Settings()
