"""
Financial calculations for the Magma Bitcoin app.

All functions use only Python standard library.
Values are returned as plain Python dicts, lists, or scalars.
"""

import math
import datetime
from typing import List, Optional, Dict, Any


# ---------------------------------------------------------------------------
# Basic time-value-of-money primitives
# ---------------------------------------------------------------------------

def present_value(future_value: float, rate: float, periods: int) -> float:
    """
    Calculate the present value of a future lump sum.

    PV = FV / (1 + rate)^periods

    Parameters
    ----------
    future_value : float
    rate         : float  — periodic interest rate (e.g. 0.05 for 5%)
    periods      : int    — number of periods

    Returns
    -------
    float
    """
    if rate == 0:
        return future_value
    return future_value / (1 + rate) ** periods


def future_value(present_value: float, rate: float, periods: int) -> float:
    """
    Calculate the future value of a present lump sum.

    FV = PV * (1 + rate)^periods

    Parameters
    ----------
    present_value : float
    rate          : float  — periodic interest rate
    periods       : int

    Returns
    -------
    float
    """
    return present_value * (1 + rate) ** periods


def annuity_payment(principal: float, rate: float, periods: int) -> float:
    """
    Calculate the periodic payment for a standard annuity (loan).

    PMT = P * r / (1 - (1+r)^-n)

    Parameters
    ----------
    principal : float  — loan or PV amount
    rate      : float  — periodic interest rate
    periods   : int    — total number of payments

    Returns
    -------
    float
    """
    if rate == 0:
        return principal / periods
    return principal * rate / (1 - (1 + rate) ** -periods)


def perpetuity_value(payment: float, rate: float) -> float:
    """
    Value of a perpetuity (infinite stream of equal payments).

    PV = PMT / rate

    Parameters
    ----------
    payment : float  — periodic payment amount
    rate    : float  — periodic discount rate

    Returns
    -------
    float
    """
    if rate == 0:
        raise ValueError("rate cannot be zero for a perpetuity")
    return payment / rate


def real_return(nominal_return: float, inflation: float) -> float:
    """
    Fisher equation: real return from nominal return and inflation.

    r_real = (1 + r_nominal) / (1 + inflation) - 1

    Parameters
    ----------
    nominal_return : float  e.g. 0.08 for 8%
    inflation      : float  e.g. 0.03 for 3%

    Returns
    -------
    float
    """
    return (1 + nominal_return) / (1 + inflation) - 1


# ---------------------------------------------------------------------------
# Compound interest & savings
# ---------------------------------------------------------------------------

def compound_interest(
    principal: float,
    rate: float,
    periods: int,
    contributions: float = 0.0,
    compound_frequency: int = 12,
) -> dict:
    """
    Compound interest with optional regular contributions.

    Parameters
    ----------
    principal          : float  — starting amount
    rate               : float  — annual interest rate (e.g. 0.07 for 7%)
    periods            : int    — number of years
    contributions      : float  — amount added each compounding period
    compound_frequency : int    — compounding periods per year (default 12 = monthly)

    Returns
    -------
    dict with:
        'final_value'      : float
        'total_contributed': float
        'total_interest'   : float
        'schedule'         : list of dicts per period {period, balance, interest, contribution}
    """
    periodic_rate = rate / compound_frequency
    total_periods = periods * compound_frequency
    balance = principal
    total_contributed = principal
    schedule = []

    for p in range(1, total_periods + 1):
        interest_earned = balance * periodic_rate
        balance += interest_earned + contributions
        total_contributed += contributions
        schedule.append({
            "period": p,
            "balance": round(balance, 8),
            "interest": round(interest_earned, 8),
            "contribution": round(contributions, 8),
        })

    total_interest = balance - total_contributed

    return {
        "final_value": round(balance, 8),
        "total_contributed": round(total_contributed, 8),
        "total_interest": round(total_interest, 8),
        "schedule": schedule,
    }


# ---------------------------------------------------------------------------
# IRR / NPV
# ---------------------------------------------------------------------------

def net_present_value(cashflows: list, rate: float) -> float:
    """
    Net Present Value of a series of cash flows.

    NPV = sum( CF_t / (1+r)^t )   for t = 0, 1, ..., n

    Parameters
    ----------
    cashflows : list of float  — index 0 is t=0 (typically negative initial investment)
    rate      : float          — discount rate per period

    Returns
    -------
    float
    """
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(cashflows))


def internal_rate_of_return(cashflows: list, guess: float = 0.1) -> float:
    """
    Internal Rate of Return using Newton-Raphson iteration.

    IRR is the rate r such that NPV(cashflows, r) = 0.

    Parameters
    ----------
    cashflows : list of float
    guess     : float  — initial rate estimate

    Returns
    -------
    float  — IRR per period; raises ValueError if no convergence

    Raises
    ------
    ValueError if IRR cannot be found in 1000 iterations
    """
    rate = guess
    for _ in range(1000):
        npv = net_present_value(cashflows, rate)
        # Derivative: d(NPV)/d(r) = sum( -t * CF_t / (1+r)^(t+1) )
        d_npv = sum(
            -t * cf / (1 + rate) ** (t + 1)
            for t, cf in enumerate(cashflows)
            if t > 0
        )
        if d_npv == 0:
            raise ValueError("Derivative is zero; cannot converge on IRR")
        new_rate = rate - npv / d_npv
        if abs(new_rate - rate) < 1e-12:
            return new_rate
        rate = new_rate

    raise ValueError("IRR did not converge after 1000 iterations")


# ---------------------------------------------------------------------------
# Loan amortization
# ---------------------------------------------------------------------------

def loan_amortization(
    principal: float,
    annual_rate: float,
    years: int,
) -> list:
    """
    Full monthly loan amortization schedule.

    Parameters
    ----------
    principal   : float  — loan amount
    annual_rate : float  — annual interest rate (e.g. 0.06 for 6%)
    years       : int    — loan term in years

    Returns
    -------
    list of dicts, one per month:
        {
          'month'            : int,
          'payment'          : float,
          'principal_paid'   : float,
          'interest_paid'    : float,
          'balance'          : float,
          'cumulative_interest': float,
        }
    """
    monthly_rate = annual_rate / 12
    n_payments = years * 12
    payment = annuity_payment(principal, monthly_rate, n_payments)

    balance = principal
    cum_interest = 0.0
    schedule = []

    for month in range(1, n_payments + 1):
        interest_paid = balance * monthly_rate
        principal_paid = payment - interest_paid
        balance -= principal_paid
        cum_interest += interest_paid

        if month == n_payments:
            # Correct rounding drift
            principal_paid += balance
            balance = 0.0

        schedule.append({
            "month": month,
            "payment": round(payment, 2),
            "principal_paid": round(principal_paid, 2),
            "interest_paid": round(interest_paid, 2),
            "balance": round(max(balance, 0.0), 2),
            "cumulative_interest": round(cum_interest, 2),
        })

    return schedule


# ---------------------------------------------------------------------------
# Debt payoff
# ---------------------------------------------------------------------------

def debt_payoff_calculator(
    debts: list,
    extra_payment: float = 0.0,
    method: str = "avalanche",
) -> dict:
    """
    Debt payoff calculator: avalanche vs snowball methods.

    Parameters
    ----------
    debts : list of dicts, each with keys:
        'name'        : str
        'balance'     : float
        'rate'        : float  — annual interest rate
        'min_payment' : float
    extra_payment : float  — extra monthly amount applied after minimums
    method        : str    — 'avalanche' (highest rate first) or 'snowball' (lowest balance first)

    Returns
    -------
    dict with:
        'method'          : str
        'months_to_payoff': int
        'total_paid'      : float
        'total_interest'  : float
        'payoff_order'    : list of debt names in payoff order
        'schedule'        : monthly summary list
    """
    import copy
    debts_copy = copy.deepcopy(debts)

    # Set priority order
    if method == "avalanche":
        debts_copy.sort(key=lambda d: d["rate"], reverse=True)
    elif method == "snowball":
        debts_copy.sort(key=lambda d: d["balance"])
    else:
        raise ValueError("method must be 'avalanche' or 'snowball'")

    total_paid = 0.0
    total_interest = 0.0
    month = 0
    schedule = []
    payoff_order = []

    while any(d["balance"] > 0 for d in debts_copy):
        month += 1
        month_interest = 0.0
        month_paid = 0.0
        extra_remaining = extra_payment

        for debt in debts_copy:
            if debt["balance"] <= 0:
                continue
            monthly_rate = debt["rate"] / 12
            interest = debt["balance"] * monthly_rate
            debt["balance"] += interest
            month_interest += interest

            payment = min(debt["min_payment"], debt["balance"])
            debt["balance"] -= payment
            month_paid += payment

        # Apply extra to priority debt
        for debt in debts_copy:
            if debt["balance"] <= 0:
                continue
            applied = min(extra_remaining, debt["balance"])
            debt["balance"] -= applied
            month_paid += applied
            extra_remaining -= applied
            if extra_remaining <= 0:
                break

        # Mark paid off debts
        for debt in debts_copy:
            if debt["balance"] <= 0.01 and debt["name"] not in payoff_order:
                payoff_order.append(debt["name"])
                debt["balance"] = 0.0

        total_paid += month_paid
        total_interest += month_interest

        schedule.append({
            "month": month,
            "total_balance": round(sum(d["balance"] for d in debts_copy), 2),
            "payment": round(month_paid, 2),
            "interest": round(month_interest, 2),
        })

        if month > 600:  # 50 years safety cap
            break

    return {
        "method": method,
        "months_to_payoff": month,
        "total_paid": round(total_paid, 2),
        "total_interest": round(total_interest, 2),
        "payoff_order": payoff_order,
        "schedule": schedule,
    }


# ---------------------------------------------------------------------------
# Inflation
# ---------------------------------------------------------------------------

def inflation_adjustment(
    amount: float,
    inflation_rate: float,
    years: int,
) -> dict:
    """
    Purchasing power erosion over time.

    Parameters
    ----------
    amount         : float  — current dollar amount
    inflation_rate : float  — annual inflation rate (e.g. 0.03)
    years          : int

    Returns
    -------
    dict with:
        'original_amount'  : float
        'inflation_rate'   : float
        'future_nominal'   : float  — amount grows at 0% real (stays same)
        'real_value_in_future': float  — what today's amount is worth in future dollars
        'purchasing_power_lost': float
        'yearly_breakdown' : list of {year, real_value, loss_percent}
    """
    yearly = []
    for y in range(1, years + 1):
        real = amount / (1 + inflation_rate) ** y
        loss = (1 - real / amount) * 100
        yearly.append({
            "year": y,
            "real_value": round(real, 4),
            "loss_percent": round(loss, 2),
        })

    final_real = amount / (1 + inflation_rate) ** years

    return {
        "original_amount": amount,
        "inflation_rate": inflation_rate,
        "years": years,
        "real_value_in_future": round(final_real, 4),
        "purchasing_power_lost": round(amount - final_real, 4),
        "loss_percent": round((1 - final_real / amount) * 100, 2),
        "yearly_breakdown": yearly,
    }


# ---------------------------------------------------------------------------
# Retirement
# ---------------------------------------------------------------------------

def retirement_calculator(
    current_age: int,
    target_age: int,
    current_savings: float,
    monthly_contribution: float,
    return_rate: float,
    inflation_rate: float = 0.03,
    withdrawal_rate: float = 0.04,
) -> dict:
    """
    Retirement nest-egg projection with withdrawal phase estimate.

    Parameters
    ----------
    current_age          : int
    target_age           : int    — desired retirement age
    current_savings      : float
    monthly_contribution : float
    return_rate          : float  — expected annual nominal return (e.g. 0.07)
    inflation_rate       : float  — expected annual inflation (default 0.03)
    withdrawal_rate      : float  — safe withdrawal rate (default 4%)

    Returns
    -------
    dict with nest_egg, annual_income, real_nest_egg, years_of_income, projection
    """
    years = target_age - current_age
    if years <= 0:
        raise ValueError("target_age must be greater than current_age")

    monthly_rate = return_rate / 12
    months = years * 12
    balance = current_savings

    projection = []
    for y in range(1, years + 1):
        for _ in range(12):
            balance += balance * monthly_rate + monthly_contribution
        real_balance = balance / (1 + inflation_rate) ** y
        projection.append({
            "year": y,
            "age": current_age + y,
            "nominal_balance": round(balance, 2),
            "real_balance": round(real_balance, 2),
        })

    real_nest_egg = balance / (1 + inflation_rate) ** years
    annual_income = balance * withdrawal_rate
    real_annual_income = real_nest_egg * withdrawal_rate
    years_of_income = 1 / withdrawal_rate  # simplistic; actual is ~30 years at 4%

    return {
        "years_to_retirement": years,
        "nest_egg_nominal": round(balance, 2),
        "nest_egg_real": round(real_nest_egg, 2),
        "annual_income_nominal": round(annual_income, 2),
        "annual_income_real": round(real_annual_income, 2),
        "monthly_contribution": monthly_contribution,
        "total_contributed": round(current_savings + monthly_contribution * months, 2),
        "total_growth": round(balance - current_savings - monthly_contribution * months, 2),
        "years_of_income_estimate": round(years_of_income, 1),
        "projection": projection,
    }


# ---------------------------------------------------------------------------
# Emergency fund
# ---------------------------------------------------------------------------

def emergency_fund_calculator(
    monthly_expenses: float,
    target_months: int,
    current_savings: float,
    monthly_saving: float,
) -> dict:
    """
    How long to reach an emergency fund target.

    Parameters
    ----------
    monthly_expenses : float  — average monthly spending
    target_months    : int    — recommended 3-6 months of expenses
    current_savings  : float  — money already saved
    monthly_saving   : float  — amount added each month

    Returns
    -------
    dict with target, gap, months_to_goal, completion_date
    """
    target = monthly_expenses * target_months
    gap = max(target - current_savings, 0.0)

    if monthly_saving <= 0:
        months_to_goal = None
        completion_date = None
    elif gap == 0:
        months_to_goal = 0
        completion_date = datetime.date.today().isoformat()
    else:
        months_to_goal = math.ceil(gap / monthly_saving)
        target_date = datetime.date.today() + datetime.timedelta(days=months_to_goal * 30.44)
        completion_date = target_date.isoformat()

    return {
        "monthly_expenses": monthly_expenses,
        "target_months": target_months,
        "target_amount": round(target, 2),
        "current_savings": round(current_savings, 2),
        "gap": round(gap, 2),
        "monthly_saving": monthly_saving,
        "months_to_goal": months_to_goal,
        "completion_date": completion_date,
        "percent_funded": round(min(current_savings / target * 100, 100), 1) if target > 0 else 100.0,
    }


# ---------------------------------------------------------------------------
# Dollar-Cost Averaging
# ---------------------------------------------------------------------------

def dollar_cost_average_analysis(
    prices: list,
    amount: float,
    frequency: str = "weekly",
) -> dict:
    """
    Simulate a DCA investment strategy over a price history.

    Parameters
    ----------
    prices    : list of float  — historical prices (chronological)
    amount    : float          — amount invested per period
    frequency : str            — 'daily', 'weekly', 'monthly'

    Returns
    -------
    dict with:
        'total_invested'     : float
        'final_value'        : float
        'total_units'        : float
        'average_cost'       : float
        'current_price'      : float
        'unrealized_gain_pct': float
        'purchases'          : list of {index, price, units, total_units, value}
    """
    freq_map = {"daily": 1, "weekly": 7, "monthly": 30}
    step = freq_map.get(frequency, 1)

    indices = list(range(0, len(prices), step))
    total_invested = 0.0
    total_units = 0.0
    purchases = []

    for idx in indices:
        p = prices[idx]
        units_bought = amount / p if p > 0 else 0.0
        total_units += units_bought
        total_invested += amount
        purchases.append({
            "index": idx,
            "price": round(p, 8),
            "units_bought": round(units_bought, 8),
            "cumulative_units": round(total_units, 8),
            "cumulative_value": round(total_units * p, 8),
        })

    current_price = prices[-1]
    final_value = total_units * current_price
    average_cost = total_invested / total_units if total_units > 0 else 0.0
    gain = final_value - total_invested
    gain_pct = (gain / total_invested * 100) if total_invested > 0 else 0.0

    return {
        "total_invested": round(total_invested, 2),
        "final_value": round(final_value, 2),
        "total_units": round(total_units, 8),
        "average_cost": round(average_cost, 8),
        "current_price": round(current_price, 2),
        "unrealized_gain": round(gain, 2),
        "unrealized_gain_pct": round(gain_pct, 2),
        "num_purchases": len(purchases),
        "purchases": purchases,
    }


# ---------------------------------------------------------------------------
# Break-even analysis
# ---------------------------------------------------------------------------

def break_even_analysis(
    fixed_costs: float,
    variable_cost_per_unit: float,
    price_per_unit: float,
) -> dict:
    """
    Break-even point for a product or service.

    Parameters
    ----------
    fixed_costs            : float  — total fixed costs per period
    variable_cost_per_unit : float  — variable cost per unit sold
    price_per_unit         : float  — selling price per unit

    Returns
    -------
    dict with break_even_units, break_even_revenue, contribution_margin, etc.
    """
    contribution_margin = price_per_unit - variable_cost_per_unit
    if contribution_margin <= 0:
        return {
            "error": "Price per unit must exceed variable cost per unit",
            "contribution_margin": contribution_margin,
        }

    contribution_margin_ratio = contribution_margin / price_per_unit
    break_even_units = fixed_costs / contribution_margin
    break_even_revenue = break_even_units * price_per_unit

    # Build a unit range for a small sensitivity table
    sensitivity = []
    for units in [
        break_even_units * 0.5,
        break_even_units * 0.75,
        break_even_units,
        break_even_units * 1.25,
        break_even_units * 1.5,
        break_even_units * 2.0,
    ]:
        revenue = units * price_per_unit
        total_var = units * variable_cost_per_unit
        profit = revenue - total_var - fixed_costs
        sensitivity.append({
            "units": round(units, 0),
            "revenue": round(revenue, 2),
            "total_cost": round(total_var + fixed_costs, 2),
            "profit": round(profit, 2),
        })

    return {
        "fixed_costs": fixed_costs,
        "variable_cost_per_unit": variable_cost_per_unit,
        "price_per_unit": price_per_unit,
        "contribution_margin": round(contribution_margin, 4),
        "contribution_margin_ratio": round(contribution_margin_ratio, 4),
        "break_even_units": round(break_even_units, 2),
        "break_even_revenue": round(break_even_revenue, 2),
        "sensitivity_table": sensitivity,
    }


# ---------------------------------------------------------------------------
# Time Value of Money solver
# ---------------------------------------------------------------------------

def time_value_of_money(
    pv: Optional[float] = None,
    fv: Optional[float] = None,
    rate: Optional[float] = None,
    nper: Optional[float] = None,
    pmt: Optional[float] = None,
) -> dict:
    """
    Solve for any one missing TVM variable given the other four.

    Parameters (pass exactly one as None to solve for it)
    ----------
    pv   : present value
    fv   : future value
    rate : periodic interest rate
    nper : number of periods
    pmt  : periodic payment (annuity; 0 for lump-sum problems)

    Returns
    -------
    dict with 'solved_for' and the computed value plus all inputs
    """
    none_count = sum(1 for v in [pv, fv, rate, nper, pmt] if v is None)
    if none_count != 1:
        raise ValueError("Exactly one parameter must be None (the variable to solve for)")

    pmt = pmt if pmt is not None else 0.0

    if pv is None:
        # PV = (FV + PMT * ((1+r)^n - 1) / r) / (1+r)^n  but simpler:
        if rate == 0:
            result = fv + pmt * nper
        else:
            result = fv / (1 + rate) ** nper + pmt * (1 - (1 + rate) ** -nper) / rate
        return {"solved_for": "pv", "pv": round(result, 8),
                "fv": fv, "rate": rate, "nper": nper, "pmt": pmt}

    if fv is None:
        if rate == 0:
            result = pv + pmt * nper
        else:
            result = pv * (1 + rate) ** nper + pmt * ((1 + rate) ** nper - 1) / rate
        return {"solved_for": "fv", "fv": round(result, 8),
                "pv": pv, "rate": rate, "nper": nper, "pmt": pmt}

    if nper is None:
        # Solve numerically using Newton-Raphson
        if rate == 0:
            if pmt == 0:
                raise ValueError("Cannot solve for nper when rate=0 and pmt=0")
            result = (fv - pv) / pmt
        else:
            # fv = pv*(1+r)^n + pmt*((1+r)^n - 1)/r
            # Rearranging: (1+r)^n = (fv + pmt/r) / (pv + pmt/r)
            a = fv + pmt / rate
            b = pv + pmt / rate
            if b == 0 or a / b <= 0:
                raise ValueError("Cannot solve for nper with given parameters")
            result = math.log(a / b) / math.log(1 + rate)
        return {"solved_for": "nper", "nper": round(result, 4),
                "pv": pv, "fv": fv, "rate": rate, "pmt": pmt}

    if rate is None:
        # Newton-Raphson on rate
        r = 0.05
        for _ in range(1000):
            if r <= -1:
                r = 0.0001
            compound = (1 + r) ** nper
            if compound == 0:
                break
            f = pv * compound + pmt * (compound - 1) / r - fv
            df = pv * nper * (1 + r) ** (nper - 1) + pmt * (
                nper * r * (1 + r) ** (nper - 1) - (compound - 1)
            ) / r ** 2
            if df == 0:
                break
            new_r = r - f / df
            if abs(new_r - r) < 1e-12:
                r = new_r
                break
            r = new_r
        return {"solved_for": "rate", "rate": round(r, 8),
                "pv": pv, "fv": fv, "nper": nper, "pmt": pmt}

    if pmt is None:
        if rate == 0:
            result = (fv - pv) / nper
        else:
            compound = (1 + rate) ** nper
            result = (fv - pv * compound) * rate / (compound - 1)
        return {"solved_for": "pmt", "pmt": round(result, 8),
                "pv": pv, "fv": fv, "rate": rate, "nper": nper}


# ---------------------------------------------------------------------------
# Weighted Average Cost of Bitcoin (WACB)
# ---------------------------------------------------------------------------

def weighted_average_cost(purchases: list) -> dict:
    """
    Weighted Average Cost Basis for a series of purchases.

    Parameters
    ----------
    purchases : list of dicts, each with:
        'amount' : float  — units purchased
        'price'  : float  — price per unit at purchase

    Returns
    -------
    dict with:
        'total_units'        : float
        'total_cost'         : float
        'average_cost_basis' : float
        'purchases'          : list with per-purchase running totals
    """
    total_units = 0.0
    total_cost = 0.0
    detailed = []

    for p in purchases:
        units = p["amount"]
        price = p["price"]
        cost = units * price
        total_units += units
        total_cost += cost
        avg = total_cost / total_units if total_units > 0 else 0.0
        detailed.append({
            "amount": units,
            "price": price,
            "cost": round(cost, 8),
            "running_units": round(total_units, 8),
            "running_cost": round(total_cost, 8),
            "running_avg_cost": round(avg, 8),
        })

    avg_cost_basis = total_cost / total_units if total_units > 0 else 0.0

    return {
        "total_units": round(total_units, 8),
        "total_cost": round(total_cost, 8),
        "average_cost_basis": round(avg_cost_basis, 8),
        "purchases": detailed,
    }


# ---------------------------------------------------------------------------
# Bond pricing
# ---------------------------------------------------------------------------

def bond_price(
    face_value: float,
    coupon_rate: float,
    market_rate: float,
    periods: int,
) -> float:
    """
    Price of a coupon bond.

    P = C * [1 - (1+r)^-n] / r  + F / (1+r)^n
    where C = coupon payment = face_value * coupon_rate

    Parameters
    ----------
    face_value  : float  — par value
    coupon_rate : float  — periodic coupon rate (e.g. 0.05 for 5% annual)
    market_rate : float  — periodic market/discount rate
    periods     : int    — number of coupon periods

    Returns
    -------
    float  — theoretical fair price
    """
    coupon = face_value * coupon_rate
    if market_rate == 0:
        return coupon * periods + face_value
    pv_coupons = coupon * (1 - (1 + market_rate) ** -periods) / market_rate
    pv_face = face_value / (1 + market_rate) ** periods
    return pv_coupons + pv_face


def yield_to_maturity(
    face_value: float,
    coupon_rate: float,
    price: float,
    periods: int,
    guess: float = 0.05,
) -> float:
    """
    Yield to Maturity using Newton-Raphson iteration.

    YTM is the periodic rate r such that:
    price = C * [1-(1+r)^-n]/r + F/(1+r)^n

    Parameters
    ----------
    face_value  : float
    coupon_rate : float  — periodic coupon rate
    price       : float  — current market price
    periods     : int
    guess       : float  — initial rate estimate

    Returns
    -------
    float  — YTM per period

    Raises
    ------
    ValueError if no convergence
    """
    coupon = face_value * coupon_rate
    r = guess

    for _ in range(1000):
        if r <= -1:
            r = 0.0001
        c = (1 + r) ** periods
        pv_c = coupon * (1 - 1 / c) / r
        pv_f = face_value / c
        f = pv_c + pv_f - price

        # Derivative
        dc = periods * (1 + r) ** (periods - 1)
        d_pv_c = coupon * (dc / c ** 2 * r - (1 - 1 / c)) / r ** 2
        d_pv_f = -face_value * dc / c ** 2

        df = d_pv_c + d_pv_f
        if df == 0:
            raise ValueError("Derivative is zero; cannot converge")

        new_r = r - f / df
        if abs(new_r - r) < 1e-12:
            return new_r
        r = new_r

    raise ValueError("YTM did not converge after 1000 iterations")

