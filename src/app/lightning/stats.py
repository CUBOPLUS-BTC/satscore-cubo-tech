"""Lightning Network analyzer — on-chain vs LN comparisons and routing insights."""

import time
from concurrent.futures import ThreadPoolExecutor
from ..services.mempool_client import MempoolClient

# Approximate cost of an on-chain transaction for routing-cost comparisons
_ONCHAIN_BASE_VBYTES = 250    # typical 1-in / 2-out P2WPKH transaction

# Minimum viable Lightning payment (routing typically requires > 1 sat)
_LN_MIN_SATS = 1

# Rough latency estimates (seconds)
_ONCHAIN_CONFIRM_SECONDS = {
    "next_block":   600,
    "30_minutes":   1800,
    "1_hour":       3600,
    "economy":      21600,   # ~6 hours
}
_LN_SETTLEMENT_SECONDS = 3   # sub-second in practice; use 3 s as conservative

# Capacity thresholds (sats) to categorise channels
_CHANNEL_SMALL   =   1_000_000   # 0.01 BTC
_CHANNEL_MEDIUM  =  10_000_000   # 0.1 BTC
_CHANNEL_LARGE   = 100_000_000   # 1 BTC

# USD/BTC reference used when on-chain fee data is unavailable
_FALLBACK_BTC_PRICE_USD = 65_000


class LightningAnalyzer:
    """Wraps MempoolClient to provide high-level Lightning Network insights."""

    def __init__(self, mempool_client: MempoolClient | None = None):
        self._client = mempool_client or MempoolClient()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_network_overview(self) -> dict:
        """Return high-level Lightning Network metrics.

        Data comes from mempool.space /v1/lightning/statistics/latest.
        Fields returned mirror what the endpoint provides, augmented with
        derived metrics (avg channel size, capacity in BTC/USD).
        """
        stats = self._safe_ln_stats()
        fees  = self._safe_fees()

        node_count    = stats.get("node_count",    0)
        channel_count = stats.get("channel_count", 0)

        # total_capacity is in satoshis on mempool.space
        total_capacity_sats = stats.get("total_capacity", 0)
        total_capacity_btc  = total_capacity_sats / 100_000_000

        avg_channel_size_sats = (
            total_capacity_sats // channel_count if channel_count > 0 else 0
        )

        # Rough capacity in USD (uses fastest fee block as proxy for current price guess;
        # without a price feed we report raw BTC)
        median_fee_rate = fees.get("halfHourFee", fees.get("fastestFee", 10))

        return {
            "node_count":              node_count,
            "channel_count":           channel_count,
            "total_capacity_sats":     total_capacity_sats,
            "total_capacity_btc":      round(total_capacity_btc, 4),
            "avg_channel_size_sats":   avg_channel_size_sats,
            "avg_channel_size_btc":    round(avg_channel_size_sats / 100_000_000, 8),
            "avg_channels_per_node":   round(channel_count / node_count, 2) if node_count else 0,
            "current_onchain_fee_sat_vb": median_fee_rate,
            "timestamp":               stats.get("latest_added", int(time.time())),
            "data_source":             "mempool.space",
        }

    def get_routing_analysis(self) -> dict:
        """Analyse fee tiers and capacity distribution across the network.

        Returns:
            fee_tiers:          Recommended on-chain fee tiers.
            capacity_bands:     Estimated share of channels per size band.
            routing_cost_model: Breakdown of what routing a payment typically costs.
        """
        fees  = self._safe_fees()
        stats = self._safe_ln_stats()

        total_cap    = stats.get("total_capacity", 0)
        chan_count   = stats.get("channel_count",  1)
        avg_chan_sat = total_cap // chan_count if chan_count else 0

        # On-chain fee cost to open/close a channel (typical 2-input 2-output TX)
        open_vbytes  = 300   # typical channel open
        close_vbytes = 250   # cooperative close

        def fee_cost(sat_vb: int, vbytes: int) -> int:
            return sat_vb * vbytes

        fastest  = fees.get("fastestFee",  30)
        half_hr  = fees.get("halfHourFee", 20)
        hour_fee = fees.get("hourFee",     10)
        economy  = fees.get("economyFee",   5)
        minimum  = fees.get("minimumFee",   1)

        # Capacity band heuristics — no per-channel data from public API,
        # so we model using the avg channel size as a distribution anchor.
        small_frac  = max(0.0, min(1.0, 1 - avg_chan_sat / _CHANNEL_MEDIUM))
        large_frac  = max(0.0, min(0.3, avg_chan_sat / _CHANNEL_LARGE))
        medium_frac = max(0.0, 1.0 - small_frac - large_frac)

        return {
            "fee_tiers": {
                "fastest_sat_vb":  fastest,
                "half_hour_sat_vb":half_hr,
                "hour_sat_vb":     hour_fee,
                "economy_sat_vb":  economy,
                "minimum_sat_vb":  minimum,
            },
            "channel_open_cost_sats": {
                "fastest":   fee_cost(fastest, open_vbytes),
                "half_hour": fee_cost(half_hr, open_vbytes),
                "hour":      fee_cost(hour_fee, open_vbytes),
                "economy":   fee_cost(economy, open_vbytes),
            },
            "channel_close_cost_sats": {
                "fastest":   fee_cost(fastest, close_vbytes),
                "half_hour": fee_cost(half_hr, close_vbytes),
                "hour":      fee_cost(hour_fee, close_vbytes),
                "economy":   fee_cost(economy, close_vbytes),
            },
            "capacity_bands": {
                "small_pct":  round(small_frac  * 100, 1),
                "medium_pct": round(medium_frac * 100, 1),
                "large_pct":  round(large_frac  * 100, 1),
                "thresholds": {
                    "small_sats":  _CHANNEL_SMALL,
                    "medium_sats": _CHANNEL_MEDIUM,
                    "large_sats":  _CHANNEL_LARGE,
                },
            },
            "avg_channel_size_sats": avg_chan_sat,
            "routing_note": (
                "LN routing fees are set by individual nodes and typically "
                "range from 0 to a few hundred ppm (parts-per-million) of "
                "the payment amount, plus a fixed base fee of 0–1 sat."
            ),
        }

    def compare_layers(self) -> dict:
        """Compare on-chain Bitcoin vs Lightning across key dimensions.

        Returns a structured comparison covering:
          fees, confirmation speed, privacy, minimum payment, use cases.
        """
        fees  = self._safe_fees()
        stats = self._safe_ln_stats()

        fastest_fee  = fees.get("fastestFee", 30)
        economy_fee  = fees.get("economyFee",  5)
        fastest_cost = fastest_fee * _ONCHAIN_BASE_VBYTES
        economy_cost = economy_fee * _ONCHAIN_BASE_VBYTES

        channel_count = stats.get("channel_count", 0)
        node_count    = stats.get("node_count",    0)

        return {
            "on_chain": {
                "description": "Native Bitcoin Layer 1 — the settlement layer",
                "fee_model":   "Per-byte fee market (sat/vB)",
                "fee_fastest_sats":  fastest_cost,
                "fee_economy_sats":  economy_cost,
                "confirmation_time": {
                    "next_block_seconds":  _ONCHAIN_CONFIRM_SECONDS["next_block"],
                    "economy_seconds":     _ONCHAIN_CONFIRM_SECONDS["economy"],
                },
                "min_practical_sats": 546,    # dust limit for P2WPKH outputs
                "privacy":     "Moderate — all TXs public on blockchain",
                "finality":    "Probabilistic — 6 confirmations ≈ irreversible",
                "best_for": [
                    "Large value transfers (> ~$50 at current fees)",
                    "Self-custody and cold storage",
                    "Opening / closing Lightning channels",
                    "Purchases requiring on-chain settlement",
                ],
            },
            "lightning": {
                "description": "Bitcoin Layer 2 — instant payment channels",
                "fee_model":   "Base fee (sats) + proportional fee (ppm)",
                "fee_typical_sats": 1,    # common for small payments
                "fee_range_ppm":    "0–1000 ppm (0–0.1% of payment)",
                "settlement_time_seconds": _LN_SETTLEMENT_SECONDS,
                "min_practical_sats": _LN_MIN_SATS,
                "privacy":     "Better — payments not individually on-chain",
                "finality":    "Instant — cryptographic commitment",
                "network_size": {
                    "nodes":    node_count,
                    "channels": channel_count,
                },
                "best_for": [
                    "Micro-payments (tips, streaming sats, small purchases)",
                    "High-frequency payments",
                    "Point-of-sale where speed matters",
                    "Remittances with low fees",
                ],
                "caveats": [
                    "Requires a funded channel (on-chain to open)",
                    "Counterparty must be online to receive",
                    "Routing may fail for large amounts",
                    "Custodial wallets sacrifice self-sovereignty",
                ],
            },
            "verdict": (
                "For amounts above ~$20 at current fees, on-chain is cost-competitive. "
                "For everyday spending, tips, and remittances under $20, "
                "Lightning is dramatically cheaper and faster."
            ),
        }

    def get_adoption_metrics(self) -> dict:
        """Return growth indicators for the Lightning Network.

        Note: mempool.space returns only the latest snapshot; we derive
        growth proxies from the available fields.
        """
        stats = self._safe_ln_stats()

        node_count    = stats.get("node_count",    0)
        channel_count = stats.get("channel_count", 0)
        total_cap     = stats.get("total_capacity", 0)

        # Derived adoption quality metrics
        channels_per_node = round(channel_count / node_count, 2) if node_count else 0
        avg_chan_btc       = round(total_cap / channel_count / 1e8, 4) if channel_count else 0
        network_density    = channels_per_node / 10.0   # normalise; well-connected node has ~10+

        maturity_label = (
            "Early adoption"  if node_count < 5_000
            else "Growing"    if node_count < 15_000
            else "Established"if node_count < 30_000
            else "Mature"
        )

        return {
            "node_count":            node_count,
            "channel_count":         channel_count,
            "total_capacity_btc":    round(total_cap / 1e8, 2),
            "channels_per_node":     channels_per_node,
            "avg_channel_size_btc":  avg_chan_btc,
            "network_density_score": round(min(1.0, network_density), 3),
            "maturity":              maturity_label,
            "adoption_insight": (
                f"With {node_count:,} nodes and {channel_count:,} channels, "
                f"the Lightning Network is in the '{maturity_label}' phase. "
                f"Each node has on average {channels_per_node} channels, "
                f"indicating {'healthy' if channels_per_node >= 5 else 'limited'} connectivity."
            ),
            "data_note": (
                "Growth trend data requires historical snapshots. "
                "This endpoint returns the latest network snapshot only."
            ),
        }

    def recommend_layer(self, amount_usd: float, urgency: str) -> dict:
        """Recommend whether to use on-chain or Lightning for a payment.

        Args:
            amount_usd: Payment size in USD.
            urgency:    "low" | "medium" | "high" | "instant"

        Returns a recommendation dict with reasoning.
        """
        if amount_usd <= 0:
            raise ValueError("amount_usd must be positive")
        if urgency not in ("low", "medium", "high", "instant"):
            raise ValueError('urgency must be one of: low, medium, high, instant')

        fees = self._safe_fees()

        fastest_fee  = fees.get("fastestFee",  30)
        economy_fee  = fees.get("economyFee",   5)
        hour_fee     = fees.get("hourFee",      15)

        # Estimate on-chain fees in USD (rough: assume $65k/BTC fallback)
        fastest_cost_sats  = fastest_fee  * _ONCHAIN_BASE_VBYTES
        economy_cost_sats  = economy_fee  * _ONCHAIN_BASE_VBYTES
        hour_cost_sats     = hour_fee     * _ONCHAIN_BASE_VBYTES

        btc_price_est = _FALLBACK_BTC_PRICE_USD
        fastest_cost_usd = fastest_cost_sats / 1e8 * btc_price_est
        economy_cost_usd = economy_cost_sats / 1e8 * btc_price_est

        # Lightning typical cost: 1 sat base + 0.01 % of amount
        ln_base_sat      = 1
        ln_ppm           = 500   # conservative middle-ground
        amount_sats      = amount_usd / btc_price_est * 1e8
        ln_routing_sats  = ln_base_sat + (amount_sats * ln_ppm / 1_000_000)
        ln_cost_usd      = ln_routing_sats / 1e8 * btc_price_est

        # Decision logic
        if urgency == "instant":
            layer = "lightning"
            reason = "Instant settlement is only possible on Lightning."
            confirm_seconds = _LN_SETTLEMENT_SECONDS
            fee_usd = ln_cost_usd
        elif amount_usd < 5:
            layer = "lightning"
            reason = (
                f"For ${amount_usd:.2f}, on-chain fees (~${fastest_cost_usd:.2f}) "
                "would exceed the payment value. Lightning is the only viable option."
            )
            confirm_seconds = _LN_SETTLEMENT_SECONDS
            fee_usd = ln_cost_usd
        elif amount_usd < 20 and urgency in ("high", "medium"):
            layer = "lightning"
            reason = (
                f"Lightning's ~${ln_cost_usd:.4f} fee is far cheaper than "
                f"on-chain (~${fastest_cost_usd:.2f}) for this amount and urgency."
            )
            confirm_seconds = _LN_SETTLEMENT_SECONDS
            fee_usd = ln_cost_usd
        elif amount_usd >= 500 or urgency == "low":
            layer = "on_chain"
            fee_usd = economy_cost_usd
            confirm_seconds = _ONCHAIN_CONFIRM_SECONDS["economy"]
            reason = (
                f"For ${amount_usd:.2f} with low urgency, on-chain economy fee "
                f"(~${economy_cost_usd:.2f}) is acceptable and provides "
                "maximum security and self-custody."
            )
        else:
            # Middle ground — compare costs
            if ln_cost_usd * 5 < fastest_cost_usd:
                layer = "lightning"
                fee_usd = ln_cost_usd
                confirm_seconds = _LN_SETTLEMENT_SECONDS
                reason = (
                    f"Lightning (~${ln_cost_usd:.4f}) is significantly cheaper "
                    f"than the fastest on-chain option (~${fastest_cost_usd:.2f})."
                )
            else:
                layer = "on_chain"
                fee_usd = hour_cost_sats / 1e8 * btc_price_est
                confirm_seconds = _ONCHAIN_CONFIRM_SECONDS["1_hour"]
                reason = (
                    f"For ${amount_usd:.2f}, on-chain with hour-fee "
                    f"(~${fee_usd:.2f}) provides good security at reasonable cost."
                )

        return {
            "recommended_layer":        layer,
            "reason":                   reason,
            "estimated_fee_usd":        round(fee_usd, 4),
            "estimated_confirm_seconds":confirm_seconds,
            "input": {
                "amount_usd": amount_usd,
                "urgency":    urgency,
            },
            "alternatives": {
                "on_chain_fastest_fee_usd": round(fastest_cost_usd, 4),
                "on_chain_economy_fee_usd": round(economy_cost_usd, 4),
                "lightning_fee_usd":        round(ln_cost_usd, 6),
            },
            "disclaimer": (
                "Fee estimates are based on current mempool conditions and a "
                f"~${btc_price_est:,} BTC price proxy. Actual fees may vary."
            ),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _safe_ln_stats(self) -> dict:
        try:
            return self._client.get_lightning_stats()
        except Exception:
            return {}

    def _safe_fees(self) -> dict:
        try:
            return self._client.get_recommended_fees()
        except Exception:
            return {}
