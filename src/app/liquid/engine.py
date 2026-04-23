"""Liquid Network analyzer — sidechain stats, asset info, and layer comparison."""

import urllib.request
import urllib.error
import json
import time
from typing import Any


# Liquid block time is ~1 minute (functionary federation)
_LIQUID_BLOCK_TIME_SECONDS = 60
_LIQUID_SETTLEMENT_SECONDS = 120  # 2 confirmations = ~2 minutes
_LIQUID_FEE_RATE = 0.1  # sat/vbyte — Liquid fees are minimal
_LIQUID_TX_VBYTES = 1200  # confidential txs are larger than Bitcoin

# Well-known Liquid asset IDs
_LBTC_ASSET_ID = "6f0279e9ed041c3d710a9f57d0c02928416460c4b722ae3457a11eec381c526d"
_USDT_ASSET_ID = "ce091c998b83c78bb71a632313ba3760f1763d9cfcffae02258ffa9865a37bd2"

# Cache TTLs
_CACHE_TTL_BLOCKS = 120  # 2 minutes
_CACHE_TTL_STATS = 300  # 5 minutes
_CACHE_TTL_ASSETS = 600  # 10 minutes


class LiquidClient:
    """HTTP client for Blockstream Esplora Liquid API."""

    _shared_cache: dict[str, tuple[Any, float]] = {}

    def __init__(self, base_url: str = "https://blockstream.info/liquid/api"):
        self.base_url = base_url

    def _cached_get(self, key: str, url: str, ttl: int) -> Any:
        now = time.time()
        if key in self._shared_cache:
            data, expiry = self._shared_cache[key]
            if now < expiry:
                return data

        req = urllib.request.Request(url, headers={"User-Agent": "Magma/1.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            raw = response.read().decode()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                # Some endpoints return plain text (e.g., block height)
                data = raw.strip()

        self._shared_cache[key] = (data, now + ttl)
        return data

    def get_block_tip_height(self) -> int:
        url = f"{self.base_url}/blocks/tip/height"
        return int(self._cached_get("liquid_tip", url, _CACHE_TTL_BLOCKS))

    def get_block_tip_hash(self) -> str:
        url = f"{self.base_url}/blocks/tip/hash"
        return str(self._cached_get("liquid_tip_hash", url, _CACHE_TTL_BLOCKS))

    def get_recent_blocks(self, count: int = 5) -> list[dict]:
        url = f"{self.base_url}/blocks"
        blocks = self._cached_get("liquid_blocks", url, _CACHE_TTL_BLOCKS)
        return blocks[:count] if isinstance(blocks, list) else []

    def get_mempool_info(self) -> dict:
        url = f"{self.base_url}/mempool"
        return self._cached_get("liquid_mempool", url, _CACHE_TTL_BLOCKS)

    def get_block_txs(self, block_hash: str) -> list[dict]:
        url = f"{self.base_url}/block/{block_hash}/txs"
        return self._cached_get(f"liquid_block_txs_{block_hash}", url, _CACHE_TTL_STATS)

    def get_asset_info(self, asset_id: str) -> dict:
        url = f"{self.base_url}/asset/{asset_id}"
        return self._cached_get(f"liquid_asset_{asset_id}", url, _CACHE_TTL_ASSETS)

    def get_address_info(self, address: str) -> dict:
        url = f"{self.base_url}/address/{address}"
        return self._cached_get(f"liquid_addr_{address}", url, _CACHE_TTL_STATS)


class LiquidAnalyzer:
    """High-level Liquid Network analysis engine."""

    def __init__(self, client: LiquidClient | None = None):
        self._client = client or LiquidClient()

    def get_network_overview(self) -> dict:
        """Return Liquid Network status and key metrics."""
        tip_height = self._safe_call(self._client.get_block_tip_height, 0)
        mempool = self._safe_call(self._client.get_mempool_info, {})
        blocks = self._safe_call(self._client.get_recent_blocks, [])

        # Calculate average tx count from recent blocks
        tx_counts = []
        for block in blocks:
            if isinstance(block, dict):
                tx_counts.append(block.get("tx_count", 0))

        avg_tx_per_block = (
            round(sum(tx_counts) / len(tx_counts), 1) if tx_counts else 0
        )

        mempool_count = mempool.get("count", 0) if isinstance(mempool, dict) else 0
        mempool_vsize = mempool.get("vsize", 0) if isinstance(mempool, dict) else 0

        # Estimated peg amount from federation (approximate from public data)
        return {
            "network": "liquid",
            "block_height": tip_height,
            "block_time_seconds": _LIQUID_BLOCK_TIME_SECONDS,
            "settlement_time_seconds": _LIQUID_SETTLEMENT_SECONDS,
            "mempool": {
                "tx_count": mempool_count,
                "vsize": mempool_vsize,
            },
            "recent_blocks": {
                "count": len(blocks),
                "avg_tx_per_block": avg_tx_per_block,
                "blocks": [
                    {
                        "height": b.get("height", 0),
                        "tx_count": b.get("tx_count", 0),
                        "timestamp": b.get("timestamp", 0),
                        "size": b.get("size", 0),
                    }
                    for b in blocks
                    if isinstance(b, dict)
                ],
            },
            "fee_rate_sat_vb": _LIQUID_FEE_RATE,
            "typical_tx_fee_sats": round(_LIQUID_FEE_RATE * _LIQUID_TX_VBYTES),
            "features": [
                "Confidential Transactions",
                "Issued Assets (USDt, L-BTC)",
                "~1 min block time",
                "Federated sidechain (Blockstream)",
                "2-way peg with Bitcoin mainchain",
            ],
            "data_source": "blockstream.info",
            "timestamp": int(time.time()),
        }

    def get_assets_info(self) -> dict:
        """Return info about key Liquid assets (L-BTC, USDt)."""
        lbtc = self._safe_call(
            lambda: self._client.get_asset_info(_LBTC_ASSET_ID), {}
        )
        usdt = self._safe_call(
            lambda: self._client.get_asset_info(_USDT_ASSET_ID), {}
        )

        def parse_asset(data: dict, fallback_name: str, fallback_ticker: str) -> dict:
            if not data:
                return {
                    "asset_id": "",
                    "name": fallback_name,
                    "ticker": fallback_ticker,
                    "precision": 8,
                    "available": False,
                }
            return {
                "asset_id": data.get("asset_id", ""),
                "name": data.get("name", fallback_name),
                "ticker": data.get("ticker", fallback_ticker),
                "precision": data.get("precision", 8),
                "chain_stats": data.get("chain_stats", {}),
                "mempool_stats": data.get("mempool_stats", {}),
                "available": True,
            }

        return {
            "l_btc": parse_asset(lbtc, "Liquid Bitcoin", "L-BTC"),
            "usdt": parse_asset(usdt, "Tether USD", "USDt"),
            "note": (
                "L-BTC is Bitcoin pegged 1:1 on the Liquid sidechain. "
                "USDt on Liquid provides dollar stability without leaving "
                "the Bitcoin ecosystem."
            ),
        }

    def compare_with_other_layers(self) -> dict:
        """Compare Liquid vs Lightning vs On-chain across key dimensions."""
        from ..services.mempool_client import MempoolClient

        mempool = MempoolClient()
        fees = self._safe_call(mempool.get_recommended_fees, {})

        fastest_fee = fees.get("fastestFee", 30)
        economy_fee = fees.get("economyFee", 5)
        onchain_fastest_sats = fastest_fee * 250  # typical tx
        onchain_economy_sats = economy_fee * 250

        liquid_fee_sats = round(_LIQUID_FEE_RATE * _LIQUID_TX_VBYTES)

        return {
            "on_chain": {
                "name": "Bitcoin (Layer 1)",
                "fee_fastest_sats": onchain_fastest_sats,
                "fee_economy_sats": onchain_economy_sats,
                "settlement_seconds": 600,
                "privacy": "Low — all transactions public",
                "min_amount_sats": 546,
                "best_for": [
                    "Large settlements",
                    "Cold storage",
                    "Maximum security",
                ],
            },
            "lightning": {
                "name": "Lightning (Layer 2)",
                "fee_typical_sats": 1,
                "fee_range": "0–1000 ppm",
                "settlement_seconds": 3,
                "privacy": "Medium — payments off-chain",
                "min_amount_sats": 1,
                "best_for": [
                    "Micropayments",
                    "Point-of-sale",
                    "Streaming sats",
                    "Remittances < $50",
                ],
            },
            "liquid": {
                "name": "Liquid (Sidechain)",
                "fee_typical_sats": liquid_fee_sats,
                "settlement_seconds": _LIQUID_SETTLEMENT_SECONDS,
                "privacy": "High — confidential transactions",
                "min_amount_sats": 1,
                "supports_assets": True,
                "best_for": [
                    "Medium-large transfers with privacy",
                    "Stablecoin transfers (USDt)",
                    "Trading between exchanges",
                    "Remittances with dollar stability",
                ],
            },
            "recommendation_matrix": {
                "micro_payment": {
                    "amount": "< $5",
                    "best": "lightning",
                    "reason": "Near-zero fees, instant settlement",
                },
                "small_transfer": {
                    "amount": "$5–$50",
                    "best": "lightning",
                    "reason": "Fast and cheap for everyday amounts",
                },
                "medium_transfer_privacy": {
                    "amount": "$50–$5,000 + privacy needed",
                    "best": "liquid",
                    "reason": "Confidential transactions, low fees, USDt option",
                },
                "medium_transfer_speed": {
                    "amount": "$50–$5,000 + speed needed",
                    "best": "lightning",
                    "reason": "Instant settlement, no confirmation wait",
                },
                "large_settlement": {
                    "amount": "> $5,000",
                    "best": "on_chain",
                    "reason": "Maximum security for large amounts",
                },
                "dollar_stability": {
                    "amount": "Any — want USD stability",
                    "best": "liquid",
                    "reason": "USDt on Liquid avoids BTC volatility",
                },
            },
        }

    def get_peg_info(self) -> dict:
        """Return information about the Liquid peg-in/peg-out process."""
        return {
            "peg_in": {
                "description": "Convert BTC to L-BTC by sending to the federation address",
                "confirmations_required": 102,
                "estimated_time": "~17 hours (102 Bitcoin blocks)",
                "minimum_amount_btc": 0.001,
                "fee": "Bitcoin network fee only (no federation fee)",
                "process": [
                    "Send BTC to the federation multisig address",
                    "Wait for 102 confirmations on Bitcoin mainchain",
                    "Receive equivalent L-BTC on Liquid Network",
                ],
            },
            "peg_out": {
                "description": "Convert L-BTC back to BTC on mainchain",
                "confirmations_required": 2,
                "estimated_time": "~2 minutes on Liquid + Bitcoin confirmation",
                "minimum_amount_btc": 0.0005,
                "fee": "~0.01% federation fee + Bitcoin network fee",
                "process": [
                    "Initiate peg-out on Liquid Network",
                    "Federation validates and signs transaction",
                    "Receive BTC on Bitcoin mainchain",
                ],
            },
            "alternatives": {
                "boltz_exchange": {
                    "description": "Atomic swap service — faster than federation peg",
                    "supports": ["BTC ↔ L-BTC", "Lightning ↔ L-BTC"],
                    "speed": "Minutes instead of hours",
                    "fee": "~0.1–0.5%",
                },
                "sideswap": {
                    "description": "Liquid DEX for swapping Liquid assets",
                    "supports": ["L-BTC ↔ USDt", "L-BTC ↔ other Liquid assets"],
                    "speed": "~2 minutes (2 Liquid blocks)",
                },
            },
            "wallets": [
                {
                    "name": "Green Wallet",
                    "by": "Blockstream",
                    "custody": "self",
                    "platforms": ["Android", "iOS", "Desktop"],
                    "features": ["L-BTC", "USDt", "Multisig", "Tor support"],
                    "description": "Blockstream's flagship wallet. Self-custody with optional 2-of-2 multisig for extra security. Supports both mainchain and Liquid. Best for privacy-focused users who want Tor routing and multisig protection.",
                },
                {
                    "name": "Aqua Wallet",
                    "by": "JAN3",
                    "custody": "self",
                    "platforms": ["Android", "iOS"],
                    "features": ["L-BTC", "USDt", "Lightning swaps", "Simple UI"],
                    "description": "Self-custody wallet designed to be simple. Swap between Lightning, on-chain and Liquid in one tap. Hold USDt on Liquid for dollar stability. Best for beginners who want Liquid without the complexity.",
                },
                {
                    "name": "SideSwap",
                    "by": "SideSwap",
                    "custody": "self",
                    "platforms": ["Android", "iOS", "Desktop"],
                    "features": ["Atomic swaps", "L-BTC", "USDt", "Trading"],
                    "description": "Decentralized exchange on Liquid. Atomic swaps between L-BTC and USDt with no intermediary. Self-custody — you sign every trade. Best for users who want to trade Liquid assets peer-to-peer.",
                },
                {
                    "name": "Marina Wallet",
                    "by": "Vulpem Ventures",
                    "custody": "self",
                    "platforms": ["Browser extension"],
                    "features": ["L-BTC", "Liquid assets", "Web3 integration"],
                    "description": "Browser extension wallet for Liquid, similar to MetaMask but for Bitcoin's sidechain. Self-custody. Interacts with Liquid-based dApps and DeFi. Best for developers and advanced users exploring Liquid ecosystem.",
                },
            ],
        }

    def recommend_layer(self, amount_usd: float, urgency: str, privacy: str = "normal") -> dict:
        """Recommend the best layer including Liquid.

        Args:
            amount_usd: Payment size in USD.
            urgency: "low" | "medium" | "high" | "instant"
            privacy: "normal" | "high" | "confidential"
        """
        if amount_usd <= 0:
            raise ValueError("amount_usd must be positive")
        if urgency not in ("low", "medium", "high", "instant"):
            raise ValueError("urgency must be one of: low, medium, high, instant")
        if privacy not in ("normal", "high", "confidential"):
            raise ValueError("privacy must be one of: normal, high, confidential")

        from ..services.mempool_client import MempoolClient

        mempool = MempoolClient()
        fees = self._safe_call(mempool.get_recommended_fees, {})

        btc_price_est = 100_000
        fastest_fee = fees.get("fastestFee", 30)
        economy_fee = fees.get("economyFee", 5)

        onchain_fast_sats = fastest_fee * 250
        onchain_econ_sats = economy_fee * 250
        onchain_fast_usd = onchain_fast_sats / 1e8 * btc_price_est
        onchain_econ_usd = onchain_econ_sats / 1e8 * btc_price_est

        amount_sats = amount_usd / btc_price_est * 1e8
        ln_sats = 1 + (amount_sats * 500 / 1_000_000)
        ln_usd = ln_sats / 1e8 * btc_price_est

        liquid_sats = round(_LIQUID_FEE_RATE * _LIQUID_TX_VBYTES)
        liquid_usd = liquid_sats / 1e8 * btc_price_est

        # Decision logic
        if privacy in ("high", "confidential"):
            layer = "liquid"
            reason = (
                "Liquid provides confidential transactions — amounts and asset types "
                "are hidden from external observers. Best option for privacy."
            )
            fee_usd = liquid_usd
            confirm_seconds = _LIQUID_SETTLEMENT_SECONDS
        elif urgency == "instant" and amount_usd < 500:
            layer = "lightning"
            reason = "Instant settlement is only possible on Lightning."
            fee_usd = ln_usd
            confirm_seconds = 3
        elif amount_usd < 5:
            layer = "lightning"
            reason = f"For ${amount_usd:.2f}, Lightning is the only cost-effective option."
            fee_usd = ln_usd
            confirm_seconds = 3
        elif amount_usd >= 50 and amount_usd <= 5000 and urgency in ("low", "medium"):
            layer = "liquid"
            reason = (
                f"For ${amount_usd:.2f} with {urgency} urgency, Liquid offers low fees "
                f"(~${liquid_usd:.4f}), confidential transactions, and settlement in ~2 min."
            )
            fee_usd = liquid_usd
            confirm_seconds = _LIQUID_SETTLEMENT_SECONDS
        elif amount_usd > 5000:
            layer = "on_chain"
            reason = (
                f"For ${amount_usd:.2f}, on-chain provides maximum security and finality."
            )
            fee_usd = onchain_econ_usd
            confirm_seconds = 3600
        elif ln_usd * 3 < onchain_fast_usd:
            layer = "lightning"
            reason = f"Lightning (~${ln_usd:.4f}) is much cheaper than on-chain (~${onchain_fast_usd:.2f})."
            fee_usd = ln_usd
            confirm_seconds = 3
        else:
            layer = "liquid"
            reason = (
                f"Liquid offers a good balance: low fees (~${liquid_usd:.4f}), "
                "fast settlement (~2 min), and confidential transactions."
            )
            fee_usd = liquid_usd
            confirm_seconds = _LIQUID_SETTLEMENT_SECONDS

        return {
            "recommended_layer": layer,
            "reason": reason,
            "estimated_fee_usd": round(fee_usd, 4),
            "estimated_confirm_seconds": confirm_seconds,
            "input": {
                "amount_usd": amount_usd,
                "urgency": urgency,
                "privacy": privacy,
            },
            "all_options": {
                "on_chain": {
                    "fee_usd": round(onchain_fast_usd, 4),
                    "confirm_seconds": 600,
                    "privacy": "low",
                },
                "lightning": {
                    "fee_usd": round(ln_usd, 6),
                    "confirm_seconds": 3,
                    "privacy": "medium",
                },
                "liquid": {
                    "fee_usd": round(liquid_usd, 4),
                    "confirm_seconds": _LIQUID_SETTLEMENT_SECONDS,
                    "privacy": "high (confidential tx)",
                },
            },
            "disclaimer": (
                "Fee estimates are based on current conditions and a "
                f"~${btc_price_est:,} BTC price proxy. Actual fees may vary."
            ),
        }

    def _safe_call(self, fn, default):
        try:
            return fn()
        except Exception:
            return default
