"""Pension projection calculator.

Projects future value of monthly Bitcoin savings using historical CAGR
to estimate growth. Compares against traditional pension funds (2% annual)
and a simple piggy bank (0% growth).
"""

from ..services.coingecko_client import CoinGeckoClient
from .schemas import PensionProjection


class PensionCalculator:
    def __init__(self):
        self.coingecko = CoinGeckoClient()

    def project(self, monthly_saving_usd: float, years: int) -> PensionProjection:
        total_months = years * 12

        current_price = self.coingecko.get_price()
        historical = self.coingecko.get_historical_prices(days=365)

        # Calculate historical CAGR from available data
        annual_growth = self._calc_cagr(historical)

        # Use a conservative estimate: 50% of historical CAGR, min 10%
        projected_annual = max(annual_growth * 0.5, 0.10)
        monthly_growth = (1 + projected_annual) ** (1 / 12) - 1

        # Traditional pension fund: 2% annual
        trad_monthly = (1.02) ** (1 / 12) - 1

        # Simulate DCA with projected growth
        total_invested = 0.0
        total_btc = 0.0
        btc_accumulated = 0.0
        trad_accumulated = 0.0
        projected_price = current_price

        breakdown = []
        monthly_data = []

        for month_idx in range(total_months):
            total_invested += monthly_saving_usd

            # BTC bought at projected price this month
            btc_bought = monthly_saving_usd / projected_price if projected_price > 0 else 0
            total_btc += btc_bought

            # Project price forward
            projected_price *= (1 + monthly_growth)

            # Value all BTC at current projected price
            btc_value = total_btc * projected_price

            # Traditional fund compounds at 2%
            trad_accumulated = (trad_accumulated + monthly_saving_usd) * (1 + trad_monthly)

            breakdown.append(
                {
                    "month": month_idx + 1,
                    "invested": round(total_invested, 2),
                    "btc_bought": round(btc_bought, 8),
                    "btc_total": round(total_btc, 8),
                    "value_usd": round(btc_value, 2),
                }
            )

            monthly_data.append(
                {
                    "month": month_idx + 1,
                    "invested": round(total_invested, 2),
                    "traditional_value": round(trad_accumulated, 2),
                    "btc_value": round(btc_value, 2),
                }
            )

        avg_buy_price = (total_invested / total_btc) if total_btc > 0 else 0.0
        final_value = breakdown[-1]["value_usd"] if breakdown else 0.0

        return PensionProjection(
            total_invested_usd=round(total_invested, 2),
            total_btc_accumulated=round(total_btc, 8),
            current_value_usd=round(final_value, 2),
            avg_buy_price=round(avg_buy_price, 2),
            current_btc_price=round(current_price, 2),
            monthly_breakdown=breakdown,
            monthly_data=monthly_data,
        )

    def _calc_cagr(self, historical: list) -> float:
        """Calculate compound annual growth rate from price history."""
        if not historical or len(historical) < 30:
            raise ValueError("Insufficient historical data to calculate CAGR")

        oldest_price = historical[0][1]
        newest_price = historical[-1][1]
        days_span = (historical[-1][0] - historical[0][0]) / (1000 * 86400)

        if days_span <= 0 or oldest_price <= 0:
            raise ValueError("Invalid historical price data")

        return ((newest_price / oldest_price) ** (365 / days_span)) - 1
