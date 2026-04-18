"""DCA projection engine using real Bitcoin historical data."""

from ..services.coingecko_client import CoinGeckoClient


class SavingsProjector:
    def __init__(self):
        self.coingecko = CoinGeckoClient()

    def project(self, monthly_usd: float, years: int = 10) -> dict:
        """Project savings growth with DCA into Bitcoin.

        Uses real historical data to calculate Bitcoin's CAGR,
        then projects forward under 3 scenarios.
        """
        prices = self.coingecko.get_historical_prices(days=365)
        current_price = self.coingecko.get_price()

        if len(prices) < 30:
            raise ValueError("Insufficient price data for projection")

        oldest_price = prices[0][1]
        newest_price = prices[-1][1]
        days_span = (prices[-1][0] - prices[0][0]) / (1000 * 86400)

        if days_span > 0 and oldest_price > 0:
            annual_return = ((newest_price / oldest_price) ** (365 / days_span)) - 1
        else:
            annual_return = 0.0

        conservative_return = max(annual_return * 0.5, 0.05)
        moderate_return = max(annual_return, 0.15)
        optimistic_return = annual_return * 1.5 if annual_return > 0 else 0.30

        total_months = years * 12
        total_invested = monthly_usd * total_months

        scenarios = []
        monthly_data = []

        for name, annual_r in [
            ("conservative", conservative_return),
            ("moderate", moderate_return),
            ("optimistic", optimistic_return),
        ]:
            monthly_r = (1 + annual_r) ** (1 / 12) - 1
            accumulated = 0.0
            for m in range(1, total_months + 1):
                accumulated = (accumulated + monthly_usd) * (1 + monthly_r)

            btc_per_month = monthly_usd / current_price
            total_btc = btc_per_month * total_months

            scenarios.append(
                {
                    "name": name,
                    "annual_return_pct": round(annual_r * 100, 1),
                    "total_invested": round(total_invested, 2),
                    "projected_value": round(accumulated, 2),
                    "total_btc": round(total_btc, 8),
                    "multiplier": round(accumulated / total_invested, 1)
                    if total_invested > 0
                    else 0,
                }
            )

        traditional_monthly_r = (1.02) ** (1 / 12) - 1
        traditional_value = 0.0
        for m in range(total_months):
            traditional_value = (traditional_value + monthly_usd) * (
                1 + traditional_monthly_r
            )

        moderate_monthly_r = (1 + moderate_return) ** (1 / 12) - 1
        trad_acc = 0.0
        btc_acc = 0.0
        for m in range(1, total_months + 1):
            trad_acc = (trad_acc + monthly_usd) * (1 + traditional_monthly_r)
            btc_acc = (btc_acc + monthly_usd) * (1 + moderate_monthly_r)
            if m % (6 if years <= 5 else 12) == 0:
                monthly_data.append(
                    {
                        "month": m,
                        "traditional": round(trad_acc, 2),
                        "btc_moderate": round(btc_acc, 2),
                        "invested": round(monthly_usd * m, 2),
                    }
                )

        return {
            "monthly_usd": monthly_usd,
            "years": years,
            "total_invested": round(total_invested, 2),
            "current_btc_price": round(current_price, 2),
            "scenarios": scenarios,
            "traditional_value": round(traditional_value, 2),
            "monthly_data": monthly_data,
            "data_source": "coingecko",
            "historical_days_used": int(days_span),
        }
