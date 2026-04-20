from typing import Any

from .http_cache import BoundedCache, cached_http_get


class MempoolClient:
    _shared_cache: BoundedCache = BoundedCache(max_size=1024)

    def __init__(self, base_url: str = "https://mempool.space/api"):
        self.base_url = base_url

    def _get(self, key: str, url: str, ttl: int) -> Any:
        return cached_http_get(
            self._shared_cache, key, url, ttl, timeout=5, retries=1
        )

    def get_address_info(self, address: str) -> dict:
        url = f"{self.base_url}/address/{address}"
        return self._get(f"addr_info_{address}", url, 300)

    def get_address_txs(self, address: str) -> list:
        url = f"{self.base_url}/address/{address}/txs"
        return self._get(f"addr_txs_{address}", url, 300)

    def get_address_utxos(self, address: str) -> list:
        url = f"{self.base_url}/address/{address}/utxo"
        return self._get(f"addr_utxos_{address}", url, 300)

    def get_lightning_stats(self) -> dict:
        url = f"{self.base_url}/v1/lightning/statistics/latest"
        return self._get("ln_stats", url, 3600)

    def get_recommended_fees(self) -> dict:
        url = f"{self.base_url}/v1/fees/recommended"
        data = self._get("fees", url, 60)
        return data if isinstance(data, dict) else {}

    def get_block_tip_height(self) -> int:
        url = f"{self.base_url}/blocks/tip/height"
        try:
            return int(self._get("block_height", url, 60))
        except (TypeError, ValueError) as exc:
            raise ValueError("Unexpected block tip height response") from exc

    def get_mempool_info(self) -> dict:
        url = f"{self.base_url}/mempool"
        return self._get("mempool_info", url, 60)
