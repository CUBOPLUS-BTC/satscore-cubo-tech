import math
from typing import Any, Optional

from .http_cache import BoundedCache, cached_http_get


class WiseClient:
    """Client for Wise (TransferWise) public comparison API."""

    _shared_cache: BoundedCache = BoundedCache(max_size=512)

    def __init__(self):
        self.base_url = "https://api.wise.com/v3"

    def _get(self, key: str, url: str, ttl: int) -> Any:
        return cached_http_get(
            self._shared_cache, key, url, ttl, timeout=10, retries=1
        )

    def get_comparison(
        self,
        amount_usd: float,
        source_country: str = "US",
        target_country: str = "SV",
        source_currency: str = "USD",
        target_currency: str = "USD",
    ) -> Optional[list[dict]]:
        """Get remittance cost comparisons from Wise API.

        Returns list of provider quotes with fee, receivedAmount, and
        delivery estimation. Returns None on any failure or when the
        response shape is unexpected.
        """
        if not isinstance(amount_usd, (int, float)) or not math.isfinite(amount_usd):
            return None
        if amount_usd <= 0:
            return None

        url = (
            f"{self.base_url}/comparisons"
            f"?sourceCurrency={source_currency}"
            f"&targetCurrency={target_currency}"
            f"&sendAmount={amount_usd}"
            f"&sourceCountry={source_country}"
            f"&targetCountry={target_country}"
        )

        cache_key = f"wise_compare_{source_country}_{target_country}_{amount_usd}"

        try:
            data = self._get(cache_key, url, 120)
        except Exception:
            return None

        if not isinstance(data, dict):
            return None

        providers = data.get("providers")
        if not isinstance(providers, list):
            return None

        results: list[dict] = []
        for provider in providers:
            if not isinstance(provider, dict):
                continue
            name = provider.get("name")
            quotes = provider.get("quotes")
            if not isinstance(name, str) or not name:
                continue
            if not isinstance(quotes, list) or not quotes:
                continue

            quote = quotes[0]
            if not isinstance(quote, dict):
                continue

            fee = _as_float(quote.get("fee"))
            received = _as_float(quote.get("receivedAmount"))
            if fee is None or received is None:
                continue
            if fee < 0 or received < 0:
                continue

            delivery = quote.get("deliveryEstimation")
            estimated_time = self._parse_delivery(
                delivery if isinstance(delivery, dict) else {}
            )

            fee_percent = (fee / amount_usd * 100) if amount_usd > 0 else 0.0

            results.append(
                {
                    "name": name,
                    "fee_usd": round(fee, 2),
                    "fee_percent": round(fee_percent, 2),
                    "amount_received": round(received, 2),
                    "estimated_time": estimated_time,
                    "is_live": True,
                }
            )

        return results if results else None

    def _parse_delivery(self, delivery: dict) -> str:
        """Parse ISO 8601 duration to human-readable time."""
        if not delivery:
            return "Unknown"

        duration = delivery.get("duration")
        if not isinstance(duration, dict):
            return "Unknown"

        min_dur = duration.get("min") or ""
        max_dur = duration.get("max") or ""

        min_hours = self._iso_to_hours(min_dur if isinstance(min_dur, str) else "")
        max_hours = self._iso_to_hours(max_dur if isinstance(max_dur, str) else "")

        if min_hours is None and max_hours is None:
            return "Unknown"

        h = max_hours if max_hours is not None else min_hours
        if h is None:
            return "Unknown"

        if h < 1:
            return "Minutes"
        if h < 24:
            return f"{int(h)} hours"
        days = h / 24
        if days <= 1.5:
            return "1 day"
        return f"{int(days)} days"

    def _iso_to_hours(self, iso_dur: str) -> Optional[float]:
        """Convert ISO 8601 duration (e.g., PT18H56M) to hours."""
        if not iso_dur or not isinstance(iso_dur, str) or not iso_dur.startswith("PT"):
            return None

        try:
            rest = iso_dur[2:]
            hours = 0.0
            if "H" in rest:
                h_part, rest = rest.split("H", 1)
                hours += float(h_part)
            if "M" in rest:
                m_part, rest = rest.split("M", 1)
                hours += float(m_part) / 60
            if "S" in rest:
                s_part = rest.replace("S", "")
                if s_part:
                    hours += float(s_part) / 3600
            return hours if math.isfinite(hours) and hours >= 0 else None
        except (ValueError, IndexError):
            return None


def _as_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None
