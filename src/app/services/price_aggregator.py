import math
from concurrent.futures import ThreadPoolExecutor, as_completed

from .coingecko_client import CoinGeckoClient
from .kraken_client import KrakenClient


class PriceUnavailableError(Exception):
    pass


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        raise ValueError("median of empty list")
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


class PriceAggregator:
    def __init__(self, coingecko_key: str = ""):
        self.coingecko = CoinGeckoClient(coingecko_key)
        self.kraken = KrakenClient()

    def get_verified_price(self) -> dict:
        prices: list[float] = []

        fetchers = [self.coingecko.get_price, self.kraken.get_price]

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(fn): fn for fn in fetchers}
            for future in as_completed(futures):
                try:
                    value = future.result()
                except Exception:
                    continue
                if (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    and value > 0
                ):
                    prices.append(float(value))

        if not prices:
            raise PriceUnavailableError("No price sources available")

        median_price = _median(prices)

        deviation = 0.0
        if len(prices) >= 2 and median_price > 0:
            max_deviation = max(abs(p - median_price) / median_price for p in prices)
            deviation = round(max_deviation * 100, 2)

        return {
            "price_usd": round(median_price, 2),
            "sources_count": len(prices),
            "deviation": deviation,
            "has_warning": len(prices) < 2,
        }
