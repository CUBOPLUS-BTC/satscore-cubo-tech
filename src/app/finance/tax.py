"""
Tax calculations for Bitcoin transactions in the Magma app.

Supports FIFO, LIFO, and HIFO cost basis accounting.
Includes US 2024 tax brackets, El Salvador special treatment (BTC as legal tender),
and comprehensive gain/loss reporting.

Pure Python standard library — no third-party dependencies.
"""

import uuid
import math
import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# ---------------------------------------------------------------------------
# Holding-period classification
# ---------------------------------------------------------------------------

def classify_holding_period(acquired_at: int, disposed_at: int) -> str:
    """
    Determine whether a holding period is short-term or long-term.

    In the US, assets held > 1 year qualify for long-term capital gains rates.

    Parameters
    ----------
    acquired_at  : int  — Unix timestamp of acquisition
    disposed_at  : int  — Unix timestamp of disposal

    Returns
    -------
    'short_term' (held < 1 year) or 'long_term' (held >= 1 year)
    """
    acquired_dt = datetime.datetime.utcfromtimestamp(acquired_at)
    disposed_dt = datetime.datetime.utcfromtimestamp(disposed_at)
    # Python timedelta comparison for > 365 days is sufficient for most cases;
    # strict IRS test is "more than one year" by calendar date.
    try:
        one_year_later = acquired_dt.replace(year=acquired_dt.year + 1)
    except ValueError:
        # Handle Feb 29 leap year edge case
        one_year_later = acquired_dt.replace(year=acquired_dt.year + 1, day=28)

    return "long_term" if disposed_dt >= one_year_later else "short_term"


def calculate_average_cost_basis(purchases: list) -> float:
    """
    Average cost basis across a list of purchases.

    Parameters
    ----------
    purchases : list of dicts, each with 'amount' (float) and 'cost_basis' (float per unit)

    Returns
    -------
    float — weighted average cost per unit
    """
    total_cost = sum(p["amount"] * p["cost_basis"] for p in purchases)
    total_amount = sum(p["amount"] for p in purchases)
    if total_amount == 0:
        return 0.0
    return total_cost / total_amount


# ---------------------------------------------------------------------------
# TaxLot dataclass
# ---------------------------------------------------------------------------

@dataclass
class TaxLot:
    """
    Represents a single unit of Bitcoin purchase (tax lot).

    Attributes
    ----------
    id          : str
    amount      : float  — BTC amount
    cost_basis  : float  — USD cost per BTC at acquisition
    acquired_at : int    — Unix timestamp
    disposed_at : Optional[int]
    proceeds    : Optional[float]  — USD received at disposal
    """
    amount: float
    cost_basis: float
    acquired_at: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    disposed_at: Optional[int] = None
    proceeds: Optional[float] = None
    disposal_amount: Optional[float] = None  # partial disposal

    @property
    def is_open(self) -> bool:
        return self.disposed_at is None

    @property
    def total_cost(self) -> float:
        return self.amount * self.cost_basis

    @property
    def holding_days(self) -> Optional[int]:
        if self.disposed_at is None:
            end = int(datetime.datetime.utcnow().timestamp())
        else:
            end = self.disposed_at
        return (end - self.acquired_at) // 86400

    @property
    def holding_period(self) -> Optional[str]:
        if self.disposed_at is None:
            return None
        return classify_holding_period(self.acquired_at, self.disposed_at)

    def realized_gain(self) -> Optional[float]:
        if self.proceeds is None or self.disposal_amount is None:
            return None
        cost = self.disposal_amount * self.cost_basis
        return self.proceeds - cost

    def to_dict(self) -> dict:
        gain = self.realized_gain()
        return {
            "id": self.id,
            "amount": self.amount,
            "cost_basis": self.cost_basis,
            "total_cost": round(self.total_cost, 8),
            "acquired_at": self.acquired_at,
            "disposed_at": self.disposed_at,
            "proceeds": self.proceeds,
            "disposal_amount": self.disposal_amount,
            "realized_gain": round(gain, 8) if gain is not None else None,
            "holding_period": self.holding_period,
            "holding_days": self.holding_days,
            "is_open": self.is_open,
        }


# ---------------------------------------------------------------------------
# TaxLotManager
# ---------------------------------------------------------------------------

class TaxLotManager:
    """
    Manages a ledger of Bitcoin tax lots and computes gains/losses.

    Supports FIFO, LIFO, and HIFO cost basis methods.
    """

    def __init__(self):
        self._open_lots: List[TaxLot] = []      # lots with remaining balance
        self._closed_lots: List[TaxLot] = []    # fully disposed lots
        self._partial_lots: List[TaxLot] = []   # lots with partial disposal record

    # -- Acquisition --------------------------------------------------------

    def add_purchase(
        self,
        amount: float,
        price_usd: float,
        timestamp: int,
        lot_id: str = None,
    ) -> TaxLot:
        """
        Record a Bitcoin purchase as a new tax lot.

        Parameters
        ----------
        amount    : float  — BTC purchased
        price_usd : float  — USD price per BTC
        timestamp : int    — Unix timestamp of purchase
        lot_id    : str    — optional custom lot ID

        Returns
        -------
        TaxLot
        """
        if amount <= 0:
            raise ValueError("amount must be positive")
        if price_usd <= 0:
            raise ValueError("price_usd must be positive")

        lot = TaxLot(
            id=lot_id or str(uuid.uuid4()),
            amount=amount,
            cost_basis=price_usd,
            acquired_at=timestamp,
        )
        self._open_lots.append(lot)
        return lot

    # -- Disposal -----------------------------------------------------------

    def process_sale(
        self,
        amount: float,
        price_usd: float,
        timestamp: int,
        method: str = "fifo",
    ) -> dict:
        """
        Process a Bitcoin sale and compute realized gains/losses.

        Parameters
        ----------
        amount    : float  — BTC sold
        price_usd : float  — USD price per BTC at sale
        timestamp : int    — Unix timestamp of sale
        method    : str    — 'fifo', 'lifo', or 'hifo'

        Returns
        -------
        dict with:
            'lots_used'          : list of lot details
            'total_proceeds'     : float
            'total_cost_basis'   : float
            'realized_gain'      : float
            'short_term_gain'    : float
            'long_term_gain'     : float
            'method'             : str
        """
        if amount <= 0:
            raise ValueError("amount must be positive")

        available = sum(lot.amount for lot in self._open_lots)
        if amount > available + 1e-8:
            raise ValueError(
                f"Insufficient BTC: trying to sell {amount}, available {available}"
            )

        # Sort open lots per method
        if method == "fifo":
            sorted_lots = sorted(self._open_lots, key=lambda l: l.acquired_at)
        elif method == "lifo":
            sorted_lots = sorted(self._open_lots, key=lambda l: l.acquired_at, reverse=True)
        elif method == "hifo":
            sorted_lots = sorted(self._open_lots, key=lambda l: l.cost_basis, reverse=True)
        else:
            raise ValueError(f"Unknown method '{method}'. Use 'fifo', 'lifo', or 'hifo'")

        remaining = amount
        total_proceeds = amount * price_usd
        total_cost = 0.0
        short_term_gain = 0.0
        long_term_gain = 0.0
        lots_used = []

        for lot in sorted_lots:
            if remaining <= 1e-10:
                break

            used = min(lot.amount, remaining)
            cost = used * lot.cost_basis
            proceeds = used * price_usd
            gain = proceeds - cost
            period = classify_holding_period(lot.acquired_at, timestamp)

            lots_used.append({
                "lot_id": lot.id,
                "acquired_at": lot.acquired_at,
                "cost_basis": lot.cost_basis,
                "amount_used": round(used, 8),
                "cost": round(cost, 8),
                "proceeds": round(proceeds, 8),
                "gain": round(gain, 8),
                "holding_period": period,
                "holding_days": (timestamp - lot.acquired_at) // 86400,
            })

            total_cost += cost
            if period == "short_term":
                short_term_gain += gain
            else:
                long_term_gain += gain

            lot.amount -= used
            remaining -= used

            if lot.amount < 1e-10:
                # Fully consumed
                lot.amount = 0.0
                lot.disposed_at = timestamp
                lot.proceeds = proceeds
                lot.disposal_amount = used
                self._open_lots.remove(lot)
                self._closed_lots.append(lot)
            else:
                # Record partial disposal info on a copy
                partial = TaxLot(
                    amount=used,
                    cost_basis=lot.cost_basis,
                    acquired_at=lot.acquired_at,
                    disposed_at=timestamp,
                    proceeds=proceeds,
                    disposal_amount=used,
                )
                self._partial_lots.append(partial)

        return {
            "method": method,
            "amount_sold": amount,
            "lots_used": lots_used,
            "total_proceeds": round(total_proceeds, 8),
            "total_cost_basis": round(total_cost, 8),
            "realized_gain": round(total_proceeds - total_cost, 8),
            "short_term_gain": round(short_term_gain, 8),
            "long_term_gain": round(long_term_gain, 8),
        }

    # -- Unrealized gains ---------------------------------------------------

    def get_unrealized_gains(self, current_price: float) -> dict:
        """
        Unrealized gains on all open lots.

        Parameters
        ----------
        current_price : float — current BTC/USD price

        Returns
        -------
        dict with summary and per-lot details
        """
        lots_detail = []
        total_btc = 0.0
        total_cost = 0.0
        total_value = 0.0
        short_term_unreal = 0.0
        long_term_unreal = 0.0
        now = int(datetime.datetime.utcnow().timestamp())

        for lot in self._open_lots:
            value = lot.amount * current_price
            cost = lot.amount * lot.cost_basis
            gain = value - cost
            period = classify_holding_period(lot.acquired_at, now)

            lots_detail.append({
                "lot_id": lot.id,
                "amount": lot.amount,
                "cost_basis": lot.cost_basis,
                "current_value": round(value, 8),
                "cost": round(cost, 8),
                "unrealized_gain": round(gain, 8),
                "gain_pct": round(gain / cost * 100, 2) if cost > 0 else 0.0,
                "holding_period": period,
                "holding_days": lot.holding_days,
            })

            total_btc += lot.amount
            total_cost += cost
            total_value += value
            if period == "short_term":
                short_term_unreal += gain
            else:
                long_term_unreal += gain

        return {
            "total_btc": round(total_btc, 8),
            "total_cost": round(total_cost, 8),
            "total_value": round(total_value, 8),
            "total_unrealized_gain": round(total_value - total_cost, 8),
            "total_gain_pct": round((total_value - total_cost) / total_cost * 100, 2) if total_cost > 0 else 0.0,
            "short_term_unrealized": round(short_term_unreal, 8),
            "long_term_unrealized": round(long_term_unreal, 8),
            "lots": lots_detail,
        }

    # -- Realized gains by year ---------------------------------------------

    def get_realized_gains(self, year: int = None) -> dict:
        """
        Realized gains from all closed and partially-disposed lots.

        Parameters
        ----------
        year : int or None  — filter to a specific tax year; None returns all

        Returns
        -------
        dict with short_term, long_term, and total realized gains
        """
        all_disposals = []

        for lot in self._closed_lots:
            if lot.disposed_at and lot.disposal_amount:
                all_disposals.append(lot)

        for lot in self._partial_lots:
            if lot.disposed_at and lot.disposal_amount:
                all_disposals.append(lot)

        if year is not None:
            all_disposals = [
                lot for lot in all_disposals
                if datetime.datetime.utcfromtimestamp(lot.disposed_at).year == year
            ]

        short_term = 0.0
        long_term = 0.0
        total_proceeds = 0.0
        total_cost = 0.0
        events = []

        for lot in all_disposals:
            proceeds = lot.proceeds or 0.0
            cost = lot.disposal_amount * lot.cost_basis
            gain = proceeds - cost
            period = classify_holding_period(lot.acquired_at, lot.disposed_at)

            total_proceeds += proceeds
            total_cost += cost
            if period == "short_term":
                short_term += gain
            else:
                long_term += gain

            events.append({
                "lot_id": lot.id,
                "acquired_at": lot.acquired_at,
                "disposed_at": lot.disposed_at,
                "amount": lot.disposal_amount,
                "cost_basis": lot.cost_basis,
                "proceeds": round(proceeds, 8),
                "gain": round(gain, 8),
                "holding_period": period,
            })

        return {
            "year": year,
            "event_count": len(events),
            "total_proceeds": round(total_proceeds, 8),
            "total_cost": round(total_cost, 8),
            "total_realized_gain": round(total_proceeds - total_cost, 8),
            "short_term_gain": round(short_term, 8),
            "long_term_gain": round(long_term, 8),
            "events": events,
        }

    # -- Full tax summary ---------------------------------------------------

    def get_tax_summary(self, year: int) -> dict:
        """
        Comprehensive tax summary for a given year.

        Returns
        -------
        dict combining realized gains, lot counts, etc.
        """
        realized = self.get_realized_gains(year)
        open_lot_count = len(self._open_lots)
        closed_lot_count = len(self._closed_lots)

        return {
            "year": year,
            "open_lots": open_lot_count,
            "closed_lots": closed_lot_count,
            **realized,
            "net_gain": round(realized["short_term_gain"] + realized["long_term_gain"], 8),
        }

    # -- Holding periods ----------------------------------------------------

    def get_holding_periods(self) -> list:
        """
        All open lots with their current holding duration.

        Returns
        -------
        list of dicts with lot details and holding info
        """
        now = int(datetime.datetime.utcnow().timestamp())
        result = []
        for lot in self._open_lots:
            days = (now - lot.acquired_at) // 86400
            period = classify_holding_period(lot.acquired_at, now)
            result.append({
                "lot_id": lot.id,
                "amount": lot.amount,
                "cost_basis": lot.cost_basis,
                "acquired_at": lot.acquired_at,
                "holding_days": days,
                "holding_period": period,
            })
        return sorted(result, key=lambda x: x["acquired_at"])

    # -- Wash sale check ----------------------------------------------------

    def get_wash_sale_check(
        self,
        sale_date: int,
        amount: float,
        window_days: int = 30,
    ) -> list:
        """
        Check for potential wash sale violations (30-day window before/after sale).

        Note: Bitcoin is NOT subject to wash sale rules in the US as of 2024,
        but this utility is provided for future regulatory compliance.

        Parameters
        ----------
        sale_date   : int  — Unix timestamp of the sale
        amount      : float
        window_days : int  — wash sale window (default 30)

        Returns
        -------
        list of lots acquired within the wash-sale window
        """
        window_sec = window_days * 86400
        start_window = sale_date - window_sec
        end_window = sale_date + window_sec

        at_risk = []
        for lot in self._open_lots:
            if start_window <= lot.acquired_at <= end_window:
                at_risk.append({
                    "lot_id": lot.id,
                    "acquired_at": lot.acquired_at,
                    "amount": lot.amount,
                    "cost_basis": lot.cost_basis,
                    "days_from_sale": abs(lot.acquired_at - sale_date) // 86400,
                })

        return at_risk

    # -- Lots by status -----------------------------------------------------

    def get_lots_by_status(self, status: str) -> list:
        """
        Return lots filtered by open/closed status.

        Parameters
        ----------
        status : 'open' or 'closed'
        """
        if status == "open":
            return [lot.to_dict() for lot in self._open_lots]
        elif status == "closed":
            all_closed = [lot.to_dict() for lot in self._closed_lots]
            all_closed += [lot.to_dict() for lot in self._partial_lots]
            return sorted(all_closed, key=lambda x: x.get("disposed_at") or 0)
        else:
            raise ValueError("status must be 'open' or 'closed'")

    # -- Cost basis method comparison ---------------------------------------

    def get_cost_basis_methods_comparison(
        self,
        amount: float,
        current_price: float,
    ) -> dict:
        """
        Compare hypothetical gains under FIFO, LIFO, and HIFO for a given sale.

        Parameters
        ----------
        amount        : float  — hypothetical sale amount (BTC)
        current_price : float  — current BTC price

        Returns
        -------
        dict with gain/tax estimates per method
        """
        import copy

        def simulate(method):
            mgr = TaxLotManager()
            for lot in self._open_lots:
                mgr._open_lots.append(copy.copy(lot))
            try:
                result = mgr.process_sale(
                    amount=amount,
                    price_usd=current_price,
                    timestamp=int(datetime.datetime.utcnow().timestamp()),
                    method=method,
                )
                return {
                    "realized_gain": result["realized_gain"],
                    "short_term": result["short_term_gain"],
                    "long_term": result["long_term_gain"],
                    "total_cost_basis": result["total_cost_basis"],
                }
            except Exception as e:
                return {"error": str(e)}

        return {
            "amount": amount,
            "current_price": current_price,
            "fifo": simulate("fifo"),
            "lifo": simulate("lifo"),
            "hifo": simulate("hifo"),
        }


# ---------------------------------------------------------------------------
# US 2024 Tax Brackets
# ---------------------------------------------------------------------------

# Format: list of (upper_bound, rate) — upper_bound=None means "above"
_US_BRACKETS_2024 = {
    "ordinary": {
        "single": [
            (11600,  0.10),
            (47150,  0.12),
            (100525, 0.22),
            (191950, 0.24),
            (243725, 0.32),
            (609350, 0.35),
            (None,   0.37),
        ],
        "married_filing_jointly": [
            (23200,   0.10),
            (94300,   0.12),
            (201050,  0.22),
            (383900,  0.24),
            (487450,  0.32),
            (731200,  0.35),
            (None,    0.37),
        ],
        "head_of_household": [
            (16550,  0.10),
            (63100,  0.12),
            (100500, 0.22),
            (191950, 0.24),
            (243700, 0.32),
            (609350, 0.35),
            (None,   0.37),
        ],
    },
    "long_term_capital_gains": {
        "single": [
            (47025,   0.00),
            (518900,  0.15),
            (None,    0.20),
        ],
        "married_filing_jointly": [
            (94050,   0.00),
            (583750,  0.15),
            (None,    0.20),
        ],
        "head_of_household": [
            (63000,   0.00),
            (551350,  0.15),
            (None,    0.20),
        ],
    },
}

# Net Investment Income Tax surtax threshold (3.8% for high earners)
_NIIT_THRESHOLD = {
    "single": 200000,
    "married_filing_jointly": 250000,
    "head_of_household": 200000,
}


def _compute_bracket_tax(income: float, brackets: list) -> float:
    """Apply progressive bracket table to income."""
    tax = 0.0
    prev_limit = 0.0
    for upper, rate in brackets:
        if upper is None:
            tax += (income - prev_limit) * rate
            break
        if income <= upper:
            tax += (income - prev_limit) * rate
            break
        tax += (upper - prev_limit) * rate
        prev_limit = upper
    return tax


def estimate_tax_liability(
    gains: dict,
    filing_status: str = "single",
    country: str = "US",
    ordinary_income: float = 0.0,
) -> dict:
    """
    Estimate tax liability on Bitcoin gains.

    Parameters
    ----------
    gains : dict with 'short_term_gain' and 'long_term_gain' keys
    filing_status : str — 'single', 'married_filing_jointly', 'head_of_household'
    country : str — 'US' or 'SV' (El Salvador)
    ordinary_income : float — other ordinary income (for bracket stacking)

    Returns
    -------
    dict with estimated federal tax liability and effective rates
    """
    st_gain = gains.get("short_term_gain", 0.0)
    lt_gain = gains.get("long_term_gain", 0.0)

    if country == "SV":
        # El Salvador: Bitcoin is legal tender (since Sept 7, 2021)
        # BTC/USD conversion gains are NOT taxed for natural persons
        # Businesses may have different rules
        return {
            "country": "El Salvador",
            "note": (
                "Bitcoin is legal tender in El Salvador (Ley Bitcoin, Art. 7). "
                "Capital gains from BTC/USD conversion are exempt for natural persons. "
                "Commercial entities may owe 30% income tax on BTC-derived profits. "
                "Consult a local tax professional."
            ),
            "short_term_gain": st_gain,
            "long_term_gain": lt_gain,
            "estimated_tax": 0.0,
            "effective_rate": 0.0,
        }

    if country != "US":
        return {
            "country": country,
            "note": f"Tax rules for {country} are not yet implemented.",
            "short_term_gain": st_gain,
            "long_term_gain": lt_gain,
        }

    if filing_status not in _US_BRACKETS_2024["ordinary"]:
        raise ValueError(
            f"Unknown filing_status '{filing_status}'. "
            f"Options: {list(_US_BRACKETS_2024['ordinary'].keys())}"
        )

    ordinary_brackets = _US_BRACKETS_2024["ordinary"][filing_status]
    ltcg_brackets = _US_BRACKETS_2024["long_term_capital_gains"][filing_status]

    # Short-term gains are taxed as ordinary income (stack on top of other income)
    base_ordinary = ordinary_income + max(st_gain, 0)
    tax_on_base = _compute_bracket_tax(base_ordinary, ordinary_brackets)
    tax_without_st = _compute_bracket_tax(ordinary_income, ordinary_brackets)
    st_tax = tax_on_base - tax_without_st

    # Long-term gains: stack on top of ordinary + short-term
    base_for_ltcg = base_ordinary  # LTCG "fills in" above ordinary income bucket
    lt_tax = _compute_bracket_tax(base_for_ltcg + max(lt_gain, 0), ltcg_brackets)
    lt_tax -= _compute_bracket_tax(base_for_ltcg, ltcg_brackets)

    # Net Investment Income Tax (3.8% surtax)
    niit_threshold = _NIIT_THRESHOLD.get(filing_status, 200000)
    net_investment_income = max(st_gain, 0) + max(lt_gain, 0)
    niit_base = max(min(ordinary_income + net_investment_income, net_investment_income)
                    - max(niit_threshold - ordinary_income, 0), 0)
    niit = niit_base * 0.038

    total_tax = st_tax + lt_tax + niit
    total_gain = st_gain + lt_gain
    effective_rate = total_tax / total_gain if total_gain > 0 else 0.0

    return {
        "country": "US",
        "tax_year": 2024,
        "filing_status": filing_status,
        "ordinary_income": ordinary_income,
        "short_term_gain": round(st_gain, 2),
        "long_term_gain": round(lt_gain, 2),
        "short_term_tax": round(st_tax, 2),
        "long_term_tax": round(lt_tax, 2),
        "niit": round(niit, 2),
        "total_estimated_tax": round(total_tax, 2),
        "effective_rate": round(effective_rate * 100, 2),
        "note": (
            "Federal estimate only. Does not include state/local taxes, "
            "deductions, credits, or self-employment tax."
        ),
    }


# ---------------------------------------------------------------------------
# Full tax report generation
# ---------------------------------------------------------------------------

def generate_tax_report(
    lots: list,
    year: int,
    country: str = "US",
    filing_status: str = "single",
) -> dict:
    """
    Generate a comprehensive tax report for a given year from a list of disposal events.

    Parameters
    ----------
    lots         : list of dicts (output from TaxLotManager.get_lots_by_status('closed'))
    year         : int  — tax year to report
    country      : str
    filing_status: str

    Returns
    -------
    dict — complete 8949-style report with summaries
    """
    year_events = []
    for lot in lots:
        disposed_at = lot.get("disposed_at")
        if not disposed_at:
            continue
        lot_year = datetime.datetime.utcfromtimestamp(disposed_at).year
        if lot_year != year:
            continue

        proceeds = lot.get("proceeds") or 0.0
        cost = (lot.get("disposal_amount") or lot.get("amount", 0)) * lot.get("cost_basis", 0)
        gain = proceeds - cost
        period = lot.get("holding_period") or classify_holding_period(
            lot.get("acquired_at", 0), disposed_at
        )

        year_events.append({
            "lot_id": lot.get("id"),
            "description": f"{lot.get('disposal_amount') or lot.get('amount', 0):.8f} BTC",
            "acquired_at": lot.get("acquired_at"),
            "disposed_at": disposed_at,
            "proceeds": round(proceeds, 2),
            "cost_basis": round(cost, 2),
            "gain_or_loss": round(gain, 2),
            "holding_period": period,
        })

    short_term_events = [e for e in year_events if e["holding_period"] == "short_term"]
    long_term_events = [e for e in year_events if e["holding_period"] == "long_term"]

    st_gain = sum(e["gain_or_loss"] for e in short_term_events)
    lt_gain = sum(e["gain_or_loss"] for e in long_term_events)

    gains = {"short_term_gain": st_gain, "long_term_gain": lt_gain}
    tax_estimate = estimate_tax_liability(gains, filing_status=filing_status, country=country)

    return {
        "tax_year": year,
        "country": country,
        "filing_status": filing_status,
        "summary": {
            "total_events": len(year_events),
            "short_term_events": len(short_term_events),
            "long_term_events": len(long_term_events),
            "total_proceeds": round(sum(e["proceeds"] for e in year_events), 2),
            "total_cost_basis": round(sum(e["cost_basis"] for e in year_events), 2),
            "short_term_gain": round(st_gain, 2),
            "long_term_gain": round(lt_gain, 2),
            "net_gain": round(st_gain + lt_gain, 2),
        },
        "tax_estimate": tax_estimate,
        "form_8949_short_term": short_term_events,
        "form_8949_long_term": long_term_events,
        "disclaimer": (
            "This report is for informational purposes only and does not constitute "
            "tax advice. Consult a qualified tax professional for your specific situation."
        ),
    }
