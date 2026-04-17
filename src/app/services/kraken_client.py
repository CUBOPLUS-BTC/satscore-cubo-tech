import urllib.request
import urllib.error
import json
import time
from typing import Any


class KrakenClient:
    def __init__(self):
        self.base_url = "https://api.kraken.com/0/public"
        self._cache: dict[str, tuple[Any, float]] = {}

    def _cached_get(self, key: str, url: str, ttl: int) -> Any:
        now = time.time()
        if key in self._cache:
            data, expiry = self._cache[key]
            if now < expiry:
                return data

        req = urllib.request.Request(url, headers={"User-Agent": "Vulk/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())

        self._cache[key] = (data, now + ttl)
        return data

    def get_price(self) -> float:
        url = f"{self.base_url}/Ticker?pair=XXBTZUSD"
        data = self._cached_get("kraken_price", url, 60)
        return float(data["result"]["XXBTZUSD"]["c"][0])
