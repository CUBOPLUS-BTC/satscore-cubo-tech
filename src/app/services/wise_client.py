import urllib.request
import urllib.error
import json
import time
from typing import Any, Optional


class WiseClient:
    """Client for Wise (TransferWise) public comparison API."""

    _shared_cache: dict[str, tuple[Any, float]] = {}

    def __init__(self):
        self.base_url = "https://api.wise.com/v3"

    def _cached_get(self, key: str, url: str, ttl: int) -> Any:
        now = time.time()
        if key in self._shared_cache:
            data, expiry = self._shared_cache[key]
            if now < expiry:
                return data

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Magma/1.0",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())

        self._shared_cache[key] = (data, now + ttl)
        return data

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
        delivery estimation. Returns None on failure.
        """
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
            data = self._cached_get(cache_key, url, 120)
        except Exception:
            return None

        providers = data.get("providers", [])
        results = []

        for provider in providers:
            name = provider.get("name", "")
            quotes = provider.get("quotes", [])
            if not quotes:
                continue

            quote = quotes[0]
            fee = quote.get("fee", 0)
            received = quote.get("receivedAmount", 0)
            delivery = quote.get("deliveryEstimation", {})

            # Parse delivery time
            estimated_time = self._parse_delivery(delivery)

            results.append(
                {
                    "name": name,
                    "fee_usd": round(fee, 2),
                    "fee_percent": round(
                        (fee / amount_usd * 100) if amount_usd > 0 else 0, 2
                    ),
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

        duration = delivery.get("duration", {})
        min_dur = duration.get("min", "")
        max_dur = duration.get("max", "")

        min_hours = self._iso_to_hours(min_dur)
        max_hours = self._iso_to_hours(max_dur)

        if min_hours is None and max_hours is None:
            return "Unknown"

        h = max_hours or min_hours or 0

        if h < 1:
            return "Minutes"
        elif h < 24:
            return f"{int(h)} hours"
        else:
            days = h / 24
            if days <= 1.5:
                return "1 day"
            else:
                return f"{int(days)} days"

    def _iso_to_hours(self, iso_dur: str) -> Optional[float]:
        """Convert ISO 8601 duration (e.g., PT18H56M) to hours."""
        if not iso_dur or not iso_dur.startswith("PT"):
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
                hours += float(s_part) / 3600
            return hours
        except (ValueError, IndexError):
            return None
