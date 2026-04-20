"""HTTP route handlers for the Liquid Network module."""

from __future__ import annotations

from ..services.liquid_client import (
    LBTC_ASSET_ID,
    USDT_ASSET_ID,
    LiquidClient,
)


_client = LiquidClient()


def _asset_summary(info: dict) -> dict:
    """Return the fields consumers actually care about."""
    if not isinstance(info, dict):
        return {}
    return {
        "asset_id": info.get("asset_id"),
        "name": info.get("name"),
        "ticker": info.get("ticker"),
        "precision": info.get("precision"),
        "issued_amount": info.get("chain_stats", {}).get("issued_amount")
        if isinstance(info.get("chain_stats"), dict)
        else None,
        "burned_amount": info.get("chain_stats", {}).get("burned_amount")
        if isinstance(info.get("chain_stats"), dict)
        else None,
    }


def handle_network_status(body: dict) -> tuple[dict, int]:
    """GET /liquid/status — block tip + fee snapshot."""
    try:
        height = _client.get_block_tip_height()
    except Exception as exc:
        return {"detail": str(exc), "available": False}, 200

    fee_sat_vb = _client.recommended_fee_sat_vb(target_blocks=2)
    estimates = _client.get_fee_estimates()

    return {
        "available": True,
        "block_height": height,
        "recommended_fee_sat_vb": round(fee_sat_vb, 4),
        "fee_estimates": estimates,
        "network": "liquid",
    }, 200


def handle_asset_info(body: dict, asset_id: str) -> tuple[dict, int]:
    """GET /liquid/asset/<asset_id>"""
    try:
        info = _client.get_asset_info(asset_id)
    except ValueError as exc:
        return {"detail": str(exc)}, 400
    except Exception as exc:
        return {"detail": str(exc)}, 502
    return _asset_summary(info), 200


def handle_lbtc(body: dict) -> tuple[dict, int]:
    """GET /liquid/lbtc — quick L-BTC asset lookup."""
    try:
        info = _client.get_lbtc_info()
    except Exception as exc:
        return {"detail": str(exc), "asset_id": LBTC_ASSET_ID}, 200
    return _asset_summary(info), 200


def handle_usdt(body: dict) -> tuple[dict, int]:
    """GET /liquid/usdt — USDt on Liquid asset lookup."""
    try:
        info = _client.get_usdt_info()
    except Exception as exc:
        return {"detail": str(exc), "asset_id": USDT_ASSET_ID}, 200
    return _asset_summary(info), 200
