from concurrent.futures import ThreadPoolExecutor, as_completed
from .coingecko_client import CoinGeckoClient
from .kraken_client import KrakenClient


class PriceUnavailableError(Exception):
    pass


class PriceAggregator:
    def __init__(self, coingecko_key: str = ""):
        self.coingecko = CoinGeckoClient(coingecko_key)
        self.kraken = KrakenClient()

    def get_verified_price(self) -> dict:
        prices = []

        fetchers = [
            self.coingecko.get_price,
            self.kraken.get_price,
        ]

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(fn): fn for fn in fetchers}
            for future in as_completed(futures):
                try:
                    prices.append(future.result())
                except Exception:
                    pass

        if not prices:
            raise PriceUnavailableError("No price sources available")

        median_price = sorted(prices)[len(prices) // 2]

        deviation = 0.0
        if len(prices) >= 2:
            max_deviation = max(abs(p - median_price) / median_price for p in prices)
            deviation = round(max_deviation * 100, 2)

        return {
            "price_usd": round(median_price, 2),
            "sources_count": len(prices),
            "deviation": deviation,
            "has_warning": len(prices) < 2,
        }

    def get_current_price(self, asset: str = "BTC") -> float:
        """Return the current price in USD for the given asset.

        Currently only BTC is supported — delegates to ``get_verified_price``.
        """
        if asset.upper() != "BTC":
            raise PriceUnavailableError(f"Unsupported asset: {asset}")
        return self.get_verified_price()["price_usd"]
