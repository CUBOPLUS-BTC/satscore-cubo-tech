"""Liquid Network (Bitcoin sidechain) endpoints."""

from __future__ import annotations

import re
from typing import Optional

from ..exceptions import MagmaError
from ..models import LiquidAsset, LiquidNetworkStatus
from ._base import Resource


_ASSET_ID_RE = re.compile(r"^[0-9a-f]{64}$")


class LiquidResource(Resource):
    def status(self) -> LiquidNetworkStatus:
        """GET /liquid/status — block tip + recommended Liquid fee."""
        data = self._get("/liquid/status")
        return LiquidNetworkStatus.from_dict(data if isinstance(data, dict) else {})

    def lbtc(self) -> LiquidAsset:
        """GET /liquid/lbtc — L-BTC asset metadata."""
        data = self._get("/liquid/lbtc")
        return LiquidAsset.from_dict(data if isinstance(data, dict) else {})

    def usdt(self) -> LiquidAsset:
        """GET /liquid/usdt — Tether USDt on Liquid asset metadata."""
        data = self._get("/liquid/usdt")
        return LiquidAsset.from_dict(data if isinstance(data, dict) else {})

    def asset(self, asset_id: str) -> LiquidAsset:
        """GET /liquid/asset/<asset_id> — arbitrary Liquid asset lookup."""
        if not isinstance(asset_id, str) or not _ASSET_ID_RE.match(asset_id):
            raise MagmaError("asset_id must be a 64-char hex string")
        data = self._get(f"/liquid/asset/{asset_id}")
        return LiquidAsset.from_dict(data if isinstance(data, dict) else {})
