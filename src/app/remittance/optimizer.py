from concurrent.futures import ThreadPoolExecutor
from ..services.coingecko_client import CoinGeckoClient
from ..services.mempool_client import MempoolClient
from .schemas import ChannelComparison, RemittanceResponse, SendTimeRecommendation
from .fees import FeeTracker


FREQUENCY_MULTIPLIERS = {
    "monthly": 1,
    "biweekly": 2,
    "weekly": 4,
}

TRADITIONAL_CHANNELS = [
    ("Western Union", 8.0, "1-3 days"),
    ("MoneyGram", 6.0, "1-2 days"),
    ("Bank Transfer", 4.0, "2-5 days"),
]


class RemittanceOptimizer:
    def __init__(self):
        self.coingecko = CoinGeckoClient()
        self.mempool = MempoolClient()
        self.fee_tracker = FeeTracker()

    def compare(
        self, amount_usd: float, frequency: str = "monthly"
    ) -> RemittanceResponse:
        with ThreadPoolExecutor(max_workers=3) as executor:
            f_price = executor.submit(self.coingecko.get_price)
            f_fees = executor.submit(self.mempool.get_recommended_fees)
            f_time = executor.submit(self.fee_tracker.get_best_send_time)

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

        fee_sat_vb = fees.get("halfHourFee", 10) if isinstance(fees, dict) else 10

        on_chain_fee_usd = (
            (fee_sat_vb * 140 / 1e8) * btc_price if btc_price > 0 else 0.5
        )
        lightning_fee_usd = max(amount_usd * 0.007, on_chain_fee_usd)
        lightning_fee_percent = (
            (lightning_fee_usd / amount_usd * 100) if amount_usd > 0 else 0.0
        )

        channels: list[ChannelComparison] = []

        for name, fee_pct, est_time in TRADITIONAL_CHANNELS:
            fee_usd = amount_usd * fee_pct / 100
            channels.append(
                ChannelComparison(
                    name=name,
                    fee_percent=round(fee_pct, 2),
                    fee_usd=round(fee_usd, 2),
                    amount_received=round(amount_usd - fee_usd, 2),
                    estimated_time=est_time,
                    is_recommended=False,
                )
            )

        channels.append(
            ChannelComparison(
                name="Lightning Network",
                fee_percent=round(lightning_fee_percent, 2),
                fee_usd=round(lightning_fee_usd, 2),
                amount_received=round(amount_usd - lightning_fee_usd, 2),
                estimated_time="Seconds",
                is_recommended=True,
            )
        )

        worst_fee_usd = max(
            ch.fee_usd for ch in channels if ch.name != "Lightning Network"
        )
        freq_multiplier = FREQUENCY_MULTIPLIERS.get(frequency, 1)
        annual_savings = (worst_fee_usd - lightning_fee_usd) * freq_multiplier * 12

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
            best_time=send_time_rec,
        )
