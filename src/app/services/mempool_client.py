import urllib.request
import urllib.error
import json
import time
from typing import Any


class MempoolClient:
    def __init__(self, base_url: str = "https://mempool.space/api"):
        self.base_url = base_url
        self._cache: dict[str, tuple[Any, float]] = {}

    def _cached_get(self, key: str, url: str, ttl: int) -> Any:
        now = time.time()
        if key in self._cache:
            data, expiry = self._cache[key]
            if now < expiry:
                return data

        req = urllib.request.Request(url, headers={"User-Agent": "Vulk/1.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode())

        self._cache[key] = (data, now + ttl)
        return data

    def get_address_info(self, address: str) -> dict:
        url = f"{self.base_url}/address/{address}"
        return self._cached_get(f"addr_info_{address}", url, 300)

    def get_address_txs(self, address: str) -> list:
        url = f"{self.base_url}/address/{address}/txs"
        return self._cached_get(f"addr_txs_{address}", url, 300)

    def get_address_utxos(self, address: str) -> list:
        url = f"{self.base_url}/address/{address}/utxo"
        return self._cached_get(f"addr_utxos_{address}", url, 300)

    def get_lightning_stats(self) -> dict:
        url = f"{self.base_url}/v1/lightning/statistics/latest"
        return self._cached_get("ln_stats", url, 3600)

    def get_recommended_fees(self) -> dict:
        url = f"{self.base_url}/v1/fees/recommended"
        return self._cached_get("fees", url, 60)
