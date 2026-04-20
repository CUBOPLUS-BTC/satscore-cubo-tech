"""Client for the Liquid Network (Blockstream sidechain).

Queries a Blockstream-compatible Esplora endpoint for block tip height,
fee estimates, block info, and asset metadata. L-BTC and Tether USDt
on Liquid are constants exposed at module scope so callers don't
have to hard-code them.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from .http_cache import BoundedCache, cached_http_get


# Well-known Liquid asset identifiers.
LBTC_ASSET_ID = "6f0279e9ed041c3d710a9f57d0c02928416460c4b722ae3457a11eec381c526d"
USDT_ASSET_ID = "ce091c998b83c78bb71a632313ba3760f1763d9cfcffae02258ffa9865a37bd2"

_ASSET_ID_RE = re.compile(r"^[0-9a-f]{64}$")


class LiquidClient:
    """Esplora client pointed at Liquid mainnet by default."""

    _shared_cache: BoundedCache = BoundedCache(max_size=512)

    def __init__(self, base_url: str = "https://blockstream.info/liquid/api"):
        self.base_url = base_url.rstrip("/")

    def _get(self, key: str, url: str, ttl: int) -> Any:
        return cached_http_get(
            self._shared_cache, key, url, ttl, timeout=5, retries=1
        )

    def _get_text(self, key: str, url: str, ttl: int) -> Optional[str]:
        """Fetch a plain-text endpoint (not JSON) with light caching."""
        import urllib.error
        import urllib.request

        cached = self._shared_cache.get(key)
        if cached is not None:
            return cached
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Magma/1.0", "Accept": "text/plain"},
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                raw = response.read().decode("utf-8", errors="replace").strip()
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            return None
        if ttl > 0:
            self._shared_cache.set(key, raw, ttl)
        return raw

    # ---- network state ----

    def get_block_tip_height(self) -> int:
        """Return the current chain tip height."""
        url = f"{self.base_url}/blocks/tip/height"
        raw = self._get_text("liquid_tip_height", url, 30)
        if raw is None:
            raise ValueError("Could not fetch Liquid tip height")
        try:
            return int(raw)
        except ValueError as exc:
            raise ValueError("Unexpected tip height response") from exc

    def get_block_tip_hash(self) -> str:
        url = f"{self.base_url}/blocks/tip/hash"
        raw = self._get_text("liquid_tip_hash", url, 30)
        if raw is None or not _ASSET_ID_RE.match(raw):
            raise ValueError("Unexpected tip hash response")
        return raw

    def get_fee_estimates(self) -> dict:
        """Return the fee estimate table keyed by confirmation target.

        Values are in sat/vB, as returned by Esplora. An empty dict
        is returned on failure so callers can fall back gracefully.
        """
        url = f"{self.base_url}/fee-estimates"
        try:
            data = self._get("liquid_fees", url, 60)
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
        cleaned: dict = {}
        for k, v in data.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                cleaned[str(k)] = float(v)
        return cleaned

    def recommended_fee_sat_vb(self, *, target_blocks: int = 2) -> float:
        """Pick a fee rate from ``get_fee_estimates`` for ``target_blocks``.

        Falls back to a conservative 0.1 sat/vB — Liquid's minimum
        relay fee is effectively constant and much lower than mainnet.
        """
        estimates = self.get_fee_estimates()
        if not estimates:
            return 0.1
        # Esplora keys are strings of block targets. Choose the smallest
        # target >= requested that still has a value.
        best: Optional[float] = None
        for key, fee in estimates.items():
            try:
                blocks = int(key)
            except (TypeError, ValueError):
                continue
            if blocks >= target_blocks:
                if best is None or fee < best:
                    best = fee
        if best is None:
            # Nothing fits the requested target — use whatever is cheapest.
            best = min(estimates.values(), default=0.1)
        return max(float(best), 0.1)

    # ---- asset info ----

    def get_asset_info(self, asset_id: str) -> dict:
        """Return metadata (ticker, precision, supply, issuer) for an asset."""
        if not isinstance(asset_id, str) or not _ASSET_ID_RE.match(asset_id):
            raise ValueError("asset_id must be a 64-char hex string")
        url = f"{self.base_url}/asset/{asset_id}"
        data = self._get(f"liquid_asset_{asset_id}", url, 3600)
        return data if isinstance(data, dict) else {}

    def get_lbtc_info(self) -> dict:
        """Shortcut for :meth:`get_asset_info` on L-BTC."""
        return self.get_asset_info(LBTC_ASSET_ID)

    def get_usdt_info(self) -> dict:
        """Shortcut for :meth:`get_asset_info` on Tether USDt."""
        return self.get_asset_info(USDT_ASSET_ID)
