from typing import Any

from .http_cache import BoundedCache, cached_http_get


class KrakenClient:
    _shared_cache: BoundedCache = BoundedCache(max_size=64)

    def __init__(self):
        self.base_url = "https://api.kraken.com/0/public"

    def _get(self, key: str, url: str, ttl: int) -> Any:
        return cached_http_get(
            self._shared_cache, key, url, ttl, timeout=10, retries=1
        )

    def get_price(self) -> float:
        url = f"{self.base_url}/Ticker?pair=XXBTZUSD"
        data = self._get("kraken_price", url, 60)
        try:
            price = float(data["result"]["XXBTZUSD"]["c"][0])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ValueError("Unexpected Kraken ticker response") from exc
        if price <= 0:
            raise ValueError("Kraken returned non-positive price")
        return price
