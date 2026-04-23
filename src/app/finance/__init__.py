"""
Finance package for Magma Bitcoin app.

Provides technical analysis indicators, financial calculators,
data models, and tax calculation utilities — all using Python
standard library only.
"""

from app.finance.indicators import (
    sma,
    ema,
    rsi,
    macd,
    bollinger_bands,
    atr,
    stochastic_oscillator,
    williams_r,
    obv,
    vwap,
    fibonacci_retracement,
    pivot_points,
    ichimoku_cloud,
    average_directional_index,
    commodity_channel_index,
    rate_of_change,
    money_flow_index,
    accumulation_distribution,
    parabolic_sar,
    analyze_trend,
)

from app.finance.calculator import (
    compound_interest,
    present_value,
    future_value,
    internal_rate_of_return,
    net_present_value,
    loan_amortization,
    debt_payoff_calculator,
    inflation_adjustment,
    retirement_calculator,
    emergency_fund_calculator,
    dollar_cost_average_analysis,
    break_even_analysis,
    time_value_of_money,
    real_return,
    weighted_average_cost,
    annuity_payment,
    perpetuity_value,
    bond_price,
    yield_to_maturity,
)

from app.finance.models import (
    PricePoint,
    OHLCV,
    Trade,
    Position,
    Portfolio,
)

from app.finance.tax import (
    TaxLot,
    TaxLotManager,
    estimate_tax_liability,
    classify_holding_period,
    generate_tax_report,
    calculate_average_cost_basis,
)

__all__ = [
    # indicators
    "sma", "ema", "rsi", "macd", "bollinger_bands",
    "atr", "stochastic_oscillator", "williams_r", "obv", "vwap",
    "fibonacci_retracement", "pivot_points", "ichimoku_cloud",
    "average_directional_index", "commodity_channel_index",
    "rate_of_change", "money_flow_index", "accumulation_distribution",
    "parabolic_sar", "analyze_trend",
    # calculator
    "compound_interest", "present_value", "future_value",
    "internal_rate_of_return", "net_present_value", "loan_amortization",
    "debt_payoff_calculator", "inflation_adjustment", "retirement_calculator",
    "emergency_fund_calculator", "dollar_cost_average_analysis",
    "break_even_analysis", "time_value_of_money", "real_return",
    "weighted_average_cost", "annuity_payment", "perpetuity_value",
    "bond_price", "yield_to_maturity",
    # models
    "PricePoint", "OHLCV", "Trade", "Position", "Portfolio",
    # tax
    "TaxLot", "TaxLotManager", "estimate_tax_liability",
    "classify_holding_period", "generate_tax_report",
    "calculate_average_cost_basis",
]
