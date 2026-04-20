from concurrent.futures import ThreadPoolExecutor
from ..services.coingecko_client import CoinGeckoClient
from ..services.mempool_client import MempoolClient
from ..services.wise_client import WiseClient
from .schemas import ChannelComparison, RemittanceResponse, SendTimeRecommendation
from .fees import FeeTracker


FREQUENCY_MULTIPLIERS = {
    "monthly": 1,
    "biweekly": 2,
    "weekly": 4,
}

# Published reference rates — used only when live data is unavailable.
# Sources:
#   Western Union: westernunion.com fee estimator (US→SV, $200, Apr 2025)
#   MoneyGram: moneygram.com fee estimator (US→SV, $200, Apr 2025)
#   Remitly: remitly.com fee estimator (US→SV, $200, Apr 2025)
#   Tigo Money: tigomoney.com.sv published rates (Apr 2025)
#   Strike: strike.me published 0% fee policy for Lightning payments
REFERENCE_CHANNELS = [
    ("Western Union", 7.5, "1–3 days"),
    ("MoneyGram", 5.5, "1–2 days"),
    ("Remitly", 3.5, "Minutes–Hours"),
    ("Tigo Money", 4.0, "1–2 days"),
    ("Strike", 0.1, "Seconds"),
]


class RemittanceOptimizer:
    def __init__(self):
        self.coingecko = CoinGeckoClient()
        self.mempool = MempoolClient()
        self.fee_tracker = FeeTracker()
        self.wise = WiseClient()

    def compare(
        self, amount_usd: float, frequency: str = "monthly"
    ) -> RemittanceResponse:
        with ThreadPoolExecutor(max_workers=4) as executor:
            f_price = executor.submit(self.coingecko.get_price)
            f_fees = executor.submit(self.mempool.get_recommended_fees)
            f_time = executor.submit(self.fee_tracker.get_best_send_time)
            f_wise = executor.submit(self.wise.get_comparison, amount_usd)

            try:
                btc_price = f_price.result()
            except Exception:
                btc_price = 0.0
            try:
                fees = f_fees.result()
            except Exception:
                fees = {}
            try:
                best_time = f_time.result()
            except Exception:
                best_time = None
            try:
                wise_data = f_wise.result()
            except Exception:
                wise_data = None

        fee_sat_vb = fees.get("halfHourFee", 10) if isinstance(fees, dict) else 10

        # --- Build traditional channels ---
        channels: list[ChannelComparison] = []

        # Merge Wise live data with reference rates
        wise_by_name: dict[str, dict] = {}
        if wise_data:
            for wp in wise_data:
                wise_by_name[wp["name"]] = wp

        for name, ref_fee_pct, ref_time in REFERENCE_CHANNELS:
            live = wise_by_name.pop(name, None)
            if live:
                channels.append(
                    ChannelComparison(
                        name=name,
                        fee_percent=live["fee_percent"],
                        fee_usd=live["fee_usd"],
                        amount_received=live["amount_received"],
                        estimated_time=live["estimated_time"],
                        is_recommended=False,
                        is_live=True,
                    )
                )
            else:
                fee_usd = amount_usd * ref_fee_pct / 100
                channels.append(
                    ChannelComparison(
                        name=name,
                        fee_percent=round(ref_fee_pct, 2),
                        fee_usd=round(fee_usd, 2),
                        amount_received=round(amount_usd - fee_usd, 2),
                        estimated_time=ref_time,
                        is_recommended=False,
                        is_live=False,
                    )
                )

        # Add any extra providers returned by Wise that aren't in our
        # reference list (e.g., Wise itself)
        for name, live in wise_by_name.items():
            channels.append(
                ChannelComparison(
                    name=name,
                    fee_percent=live["fee_percent"],
                    fee_usd=live["fee_usd"],
                    amount_received=live["amount_received"],
                    estimated_time=live["estimated_time"],
                    is_recommended=False,
                    is_live=True,
                )
            )

        # --- Lightning Network (always live) ---
        on_chain_fee_usd = (
            (fee_sat_vb * 140 / 1e8) * btc_price if btc_price > 0 else 0.5
        )
        lightning_fee_usd = max(amount_usd * 0.003, on_chain_fee_usd)
        lightning_fee_percent = (
            (lightning_fee_usd / amount_usd * 100) if amount_usd > 0 else 0.0
        )

        channels.append(
            ChannelComparison(
                name="Lightning Network",
                fee_percent=round(lightning_fee_percent, 2),
                fee_usd=round(lightning_fee_usd, 2),
                amount_received=round(amount_usd - lightning_fee_usd, 2),
                estimated_time="Seconds",
                is_recommended=True,
                is_live=True,
            )
        )

        # --- Savings calculation ---
        worst_channel = max(
            (ch for ch in channels if ch.name != "Lightning Network"),
            key=lambda c: c.fee_usd,
        )
        worst_fee_usd = worst_channel.fee_usd
        worst_channel_name = worst_channel.name
        savings_vs_worst = round(worst_fee_usd - lightning_fee_usd, 2)
        freq_multiplier = FREQUENCY_MULTIPLIERS.get(frequency, 1)
        annual_savings = savings_vs_worst * freq_multiplier * 12

        # --- Best send time ---
        send_time_rec = None
        if best_time and isinstance(best_time, dict):
            estimated_low = best_time.get("estimated_low_fee_sat_vb", fee_sat_vb)
            savings_pct = (
                (fee_sat_vb - estimated_low) / fee_sat_vb * 100
                if fee_sat_vb > 0
                else 0.0
            )
            send_time_rec = SendTimeRecommendation(
                best_time=best_time.get("best_time", "Weekends 2-6 AM UTC"),
                current_fee_sat_vb=fee_sat_vb,
                estimated_low_fee_sat_vb=estimated_low,
                savings_percent=round(savings_pct, 2),
            )

        return RemittanceResponse(
            channels=channels,
            annual_savings=round(annual_savings, 2),
            best_channel="Lightning Network",
            savings_vs_worst=savings_vs_worst,
            worst_channel_name=worst_channel_name,
            best_time=send_time_rec,
        )
