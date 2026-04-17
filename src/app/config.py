import os
import json
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./vulk.db")
    JWT_SECRET: str = os.environ.get("JWT_SECRET", "dev-secret-change-in-prod")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.environ.get("JWT_EXPIRE_MINUTES", "30"))
    MEMPOOL_API_URL: str = os.environ.get(
        "MEMPOOL_API_URL", "https://mempool.space/api"
    )
    COINGECKO_API_KEY: str = os.environ.get("COINGECKO_API_KEY", "")

    @property
    def CORS_ORIGINS(self) -> list:
        raw = os.environ.get("CORS_ORIGINS", '["http://localhost:8080"]')
        if isinstance(raw, str):
            return json.loads(raw)
        return raw


settings = Settings()
