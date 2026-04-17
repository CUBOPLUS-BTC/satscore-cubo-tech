import urllib.request
import urllib.error
import json
import time
from typing import Any


class CoinGeckoClient:
    def __init__(self, api_key: str = ""):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.api_key = api_key
        self._cache: dict[str, tuple[Any, float]] = {}

    def _headers(self) -> dict:
        headers = {"User-Agent": "Vulk/1.0"}
        if self.api_key:
            headers["x-cg-demo-api-key"] = self.api_key
        return headers

    def _cached_get(self, key: str, url: str, ttl: int) -> Any:
        now = time.time()
        if key in self._cache:
            data, expiry = self._cache[key]
            if now < expiry:
                return data

        req = urllib.request.Request(url, headers=self._headers())
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())

        self._cache[key] = (data, now + ttl)
        return data

    def get_price(self) -> float:
        url = f"{self.base_url}/simple/price?ids=bitcoin&vs_currencies=usd"
        data = self._cached_get("btc_price", url, 60)
        return float(data["bitcoin"]["usd"])

    def get_historical_prices(self, days: int = 90) -> list:
        url = f"{self.base_url}/coins/bitcoin/market_chart?vs_currency=usd&days={days}"
        data = self._cached_get(f"historical_{days}", url, 3600)
        return data.get("prices", [])
