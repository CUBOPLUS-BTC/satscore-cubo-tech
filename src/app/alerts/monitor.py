"""Background alert monitor — polls mempool and price APIs."""

import threading
import time
import secrets
from ..services.mempool_client import MempoolClient
from ..services.price_aggregator import PriceAggregator
from ..auth.lnurl import cleanup_expired as cleanup_lnurl
from ..auth.sessions import cleanup_expired as cleanup_sessions


class AlertMonitor:
    def __init__(self, price_aggregator: PriceAggregator):
        self.mempool = MempoolClient()
        self.price_agg = price_aggregator
        self._alerts: list[dict] = []
        self._lock = threading.Lock()
        self._running = False
        self._last_price: float = 0.0
        self._last_fee: int = 0

    def start(self) -> None:
        """Start the background monitoring thread."""
        self._running = True
        t = threading.Thread(target=self._run_loop, daemon=True, name="alert-monitor")
        t.start()

    def stop(self) -> None:
        self._running = False

    def _run_loop(self) -> None:
        tick = 0
        while self._running:
            try:
                self._check_fees()
            except Exception:
                pass
            try:
                self._check_price()
            except Exception:
                pass
            # Cleanup expired sessions/challenges every 5 minutes
            tick += 1
            if tick % 5 == 0:
                cleanup_lnurl()
                cleanup_sessions()
            time.sleep(60)

    def _check_fees(self) -> None:
        fees = self.mempool.get_recommended_fees()
        if not isinstance(fees, dict):
            return

        half_hour = fees.get("halfHourFee", 0)

        if self._last_fee > 0 and abs(half_hour - self._last_fee) < 3:
            return

        self._last_fee = half_hour

        if half_hour <= 5:
            self._add_alert(
                "fee_low",
                f"Fees are very low ({half_hour} sat/vB) — good time for on-chain transactions",
                {"fee_sat_vb": half_hour, "recommendation": "on-chain"},
            )
        elif half_hour >= 50:
            self._add_alert(
                "fee_high",
                f"Fees are high ({half_hour} sat/vB) — use Lightning Network instead",
                {"fee_sat_vb": half_hour, "recommendation": "lightning"},
            )

    def _check_price(self) -> None:
        try:
            price_data = self.price_agg.get_verified_price()
            price = price_data.get("price_usd", 0)
        except Exception:
            return

        if self._last_price > 0 and price > 0:
            change_pct = abs(price - self._last_price) / self._last_price * 100
            if change_pct >= 5:
                direction = "up" if price > self._last_price else "down"
                self._add_alert(
                    "price_move",
                    f"BTC moved {change_pct:.1f}% {direction} — now ${price:,.0f}",
                    {
                        "price_usd": price,
                        "change_pct": round(change_pct, 1),
                        "direction": direction,
                    },
                )

        self._last_price = price

    def _add_alert(self, alert_type: str, message: str, data: dict) -> None:
        with self._lock:
            alert = {
                "id": secrets.token_hex(8),
                "type": alert_type,
                "message": message,
                "data": data,
                "created_at": int(time.time()),
            }
            self._alerts.append(alert)
            if len(self._alerts) > 100:
                self._alerts = self._alerts[-100:]

    def get_alerts(self, since: int = 0) -> list[dict]:
        """Get alerts since a given timestamp."""
        with self._lock:
            return [a for a in self._alerts if a["created_at"] > since]

    def get_current_status(self) -> dict:
        """Get current fee/price status with recommendation."""
        try:
            fees = self.mempool.get_recommended_fees()
        except Exception:
            fees = {}

        try:
            price_data = self.price_agg.get_verified_price()
        except Exception:
            price_data = {"price_usd": 0, "sources_count": 0, "has_warning": True}

        half_hour = fees.get("halfHourFee", 0) if isinstance(fees, dict) else 0
        economy = fees.get("economyFee", 0) if isinstance(fees, dict) else 0

        if half_hour <= 5:
            recommendation = "on-chain"
            message = "Low fees — good for on-chain transactions"
        elif half_hour <= 20:
            recommendation = "either"
            message = "Moderate fees — both channels work"
        else:
            recommendation = "lightning"
            message = "High fees — use Lightning Network"

        return {
            "fees": fees if isinstance(fees, dict) else {},
            "price": price_data,
            "recommendation": recommendation,
            "message": message,
            "half_hour_fee": half_hour,
            "economy_fee": economy,
        }
