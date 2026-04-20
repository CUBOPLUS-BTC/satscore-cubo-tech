from typing import Any

from .http_cache import BoundedCache, cached_http_get


class CoinGeckoClient:
    _shared_cache: BoundedCache = BoundedCache(max_size=256)

    def __init__(self, api_key: str = ""):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.api_key = api_key

    def _headers(self) -> dict:
        headers = {"User-Agent": "Magma/1.0"}
        if self.api_key:
            headers["x-cg-demo-api-key"] = self.api_key
        return headers

    def _get(self, key: str, url: str, ttl: int) -> Any:
        return cached_http_get(
            self._shared_cache,
            key,
            url,
            ttl,
            timeout=8,
            headers=self._headers(),
            retries=2,
        )

    def get_price(self) -> float:
        url = f"{self.base_url}/simple/price?ids=bitcoin&vs_currencies=usd"
        data = self._get("btc_price", url, 60)
        try:
            price = float(data["bitcoin"]["usd"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Unexpected CoinGecko price response") from exc
        if price <= 0:
            raise ValueError("CoinGecko returned non-positive price")
        return price

    def get_historical_prices(self, days: int = 90) -> list:
        if days <= 0:
            raise ValueError("days must be positive")
        url = f"{self.base_url}/coins/bitcoin/market_chart?vs_currency=usd&days={days}"
        data = self._get(f"historical_{days}", url, 3600)
        prices = data.get("prices", []) if isinstance(data, dict) else []
        return [
            p
            for p in prices
            if isinstance(p, (list, tuple))
            and len(p) >= 2
            and isinstance(p[0], (int, float))
            and isinstance(p[1], (int, float))
            and p[1] > 0
        ]
