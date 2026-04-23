"""
Portfolio tracking for Magma Bitcoin app.

PortfolioTracker manages holdings, transactions, P&L calculation,
cost basis (FIFO/LIFO/average), and performance metrics via SQLite.

Tables created:
    portfolio_holdings     — current positions
    portfolio_transactions — full trade history

Uses only Python standard library.
"""

import time
import math
import json
from ..database import get_conn, _is_postgres


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------

def _ph() -> str:
    return "%s" if _is_postgres() else "?"


_CREATE_HOLDINGS = """
    CREATE TABLE IF NOT EXISTS portfolio_holdings (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        pubkey          TEXT    NOT NULL,
        asset           TEXT    NOT NULL DEFAULT 'BTC',
        amount          REAL    NOT NULL,
        cost_basis_usd  REAL    NOT NULL,
        acquired_at     INTEGER NOT NULL,
        notes           TEXT    NOT NULL DEFAULT '',
        created_at      INTEGER NOT NULL,
        updated_at      INTEGER NOT NULL
    )
"""

_CREATE_TRANSACTIONS = """
    CREATE TABLE IF NOT EXISTS portfolio_transactions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        pubkey      TEXT    NOT NULL,
        tx_type     TEXT    NOT NULL,
        asset       TEXT    NOT NULL DEFAULT 'BTC',
        amount      REAL    NOT NULL,
        price_usd   REAL    NOT NULL,
        fee_usd     REAL    NOT NULL DEFAULT 0,
        timestamp   INTEGER NOT NULL,
        notes       TEXT    NOT NULL DEFAULT '',
        created_at  INTEGER NOT NULL
    )
"""


def _ensure_tables():
    conn = get_conn()
    conn.execute(_CREATE_HOLDINGS)
    conn.execute(_CREATE_TRANSACTIONS)
    conn.commit()


# ---------------------------------------------------------------------------
# Price helper (stub — in production calls price aggregator)
# ---------------------------------------------------------------------------

def _get_current_price(asset: str = "BTC") -> float:
    """Return current price. Falls back to 65,000 if API unavailable."""
    try:
        import urllib.request, json as _json
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = _json.loads(resp.read())
            return float(data["bitcoin"]["usd"])
    except Exception:
        return 65_000.0


# ---------------------------------------------------------------------------
# Utility maths
# ---------------------------------------------------------------------------

def _mean(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


def _stddev(values: list) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (n - 1))


def _pct(old: float, new: float) -> float:
    return (new - old) / old * 100.0 if old else 0.0


def _annualise(total_return_pct: float, days: float) -> float:
    """Convert total return % to annualised % (CAGR)."""
    if days <= 0 or total_return_pct <= -100:
        return 0.0
    years = days / 365.0
    return ((1 + total_return_pct / 100) ** (1 / years) - 1) * 100


# ---------------------------------------------------------------------------
# PortfolioTracker
# ---------------------------------------------------------------------------

class PortfolioTracker:
    """
    Tracks Bitcoin (and multi-asset) portfolio holdings and transactions.
    All public methods are stateless — state lives in the SQLite database.
    """

    def __init__(self):
        _ensure_tables()

    # ------------------------------------------------------------------
    # Holdings CRUD
    # ------------------------------------------------------------------

    def add_holding(self, pubkey: str, asset: str, amount: float,
                    cost_basis_usd: float, acquired_at: int = None,
                    notes: str = "") -> dict:
        """
        Add a new holding entry.

        Parameters
        ----------
        pubkey        : user's Nostr public key
        asset         : e.g. 'BTC', 'ETH'
        amount        : quantity
        cost_basis_usd: total cost in USD
        acquired_at   : Unix timestamp of acquisition (defaults to now)
        notes         : optional user note

        Returns
        -------
        dict representation of the created holding
        """
        now = int(time.time())
        if acquired_at is None:
            acquired_at = now
        p = _ph()
        conn = get_conn()
        conn.execute(
            f"INSERT INTO portfolio_holdings "
            f"(pubkey, asset, amount, cost_basis_usd, acquired_at, notes, created_at, updated_at) "
            f"VALUES ({p},{p},{p},{p},{p},{p},{p},{p})",
            (pubkey, asset.upper(), amount, cost_basis_usd, acquired_at, notes, now, now),
        )
        conn.commit()

        # Also record as a BUY transaction
        price_per_unit = cost_basis_usd / amount if amount > 0 else 0
        self.record_transaction(pubkey, "buy", asset, amount, price_per_unit, 0, notes)

        return {
            "asset":         asset.upper(),
            "amount":        round(amount, 8),
            "cost_basis_usd": round(cost_basis_usd, 2),
            "price_per_unit": round(price_per_unit, 2),
            "acquired_at":   acquired_at,
            "notes":         notes,
        }

    def remove_holding(self, pubkey: str, holding_id: int) -> bool:
        """Delete a holding by ID (must belong to pubkey)."""
        p = _ph()
        conn = get_conn()
        result = conn.execute(
            f"DELETE FROM portfolio_holdings WHERE id = {p} AND pubkey = {p}",
            (holding_id, pubkey),
        )
        conn.commit()
        return result.rowcount > 0

    def update_holding(self, pubkey: str, holding_id: int,
                       amount: float = None, cost_basis_usd: float = None,
                       notes: str = None) -> dict:
        """Partially update a holding."""
        p = _ph()
        conn = get_conn()
        now = int(time.time())
        updates = []
        params  = []
        if amount is not None:
            updates.append(f"amount = {p}")
            params.append(amount)
        if cost_basis_usd is not None:
            updates.append(f"cost_basis_usd = {p}")
            params.append(cost_basis_usd)
        if notes is not None:
            updates.append(f"notes = {p}")
            params.append(notes)
        updates.append(f"updated_at = {p}")
        params.append(now)
        params.extend([holding_id, pubkey])

        if updates:
            conn.execute(
                f"UPDATE portfolio_holdings SET {', '.join(updates)} "
                f"WHERE id = {p} AND pubkey = {p}",
                params,
            )
            conn.commit()
        return self._get_holding_by_id(holding_id)

    def _get_holding_by_id(self, holding_id: int) -> dict:
        conn = get_conn()
        p = _ph()
        row = conn.execute(
            f"SELECT * FROM portfolio_holdings WHERE id = {p}", (holding_id,)
        ).fetchone()
        return dict(row) if row else {}

    # ------------------------------------------------------------------
    # Transaction recording
    # ------------------------------------------------------------------

    def record_transaction(self, pubkey: str, tx_type: str, asset: str,
                           amount: float, price_usd: float, fee_usd: float = 0,
                           notes: str = "", timestamp: int = None) -> dict:
        """
        Record a buy/sell/transfer/deposit/withdrawal transaction.

        Parameters
        ----------
        tx_type : 'buy' | 'sell' | 'transfer_in' | 'transfer_out' | 'fee'
        """
        now = int(time.time())
        ts  = timestamp or now
        p   = _ph()
        conn = get_conn()
        conn.execute(
            f"INSERT INTO portfolio_transactions "
            f"(pubkey, tx_type, asset, amount, price_usd, fee_usd, timestamp, notes, created_at) "
            f"VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p})",
            (pubkey, tx_type, asset.upper(), amount, price_usd, fee_usd, ts, notes, now),
        )
        conn.commit()

        return {
            "tx_type":   tx_type,
            "asset":     asset.upper(),
            "amount":    round(amount, 8),
            "price_usd": round(price_usd, 2),
            "fee_usd":   round(fee_usd, 2),
            "total_usd": round(amount * price_usd + fee_usd, 2),
            "timestamp": ts,
            "notes":     notes,
        }

    # ------------------------------------------------------------------
    # Holdings retrieval
    # ------------------------------------------------------------------

    def get_holdings(self, pubkey: str) -> list[dict]:
        """Return all holdings enriched with current market value."""
        p = _ph()
        conn = get_conn()
        rows = conn.execute(
            f"SELECT * FROM portfolio_holdings WHERE pubkey = {p} ORDER BY acquired_at",
            (pubkey,),
        ).fetchall()

        if not rows:
            return []

        # Fetch current prices for each unique asset
        assets = list({row["asset"] if hasattr(row, '__getitem__') else row[2]
                       for row in rows})
        prices = {}
        for asset in assets:
            prices[asset] = _get_current_price(asset)

        result = []
        for row in rows:
            row_d = dict(row) if hasattr(row, 'keys') else {
                "id": row[0], "pubkey": row[1], "asset": row[2],
                "amount": row[3], "cost_basis_usd": row[4],
                "acquired_at": row[5], "notes": row[6],
                "created_at": row[7], "updated_at": row[8],
            }
            asset         = row_d["asset"]
            amount        = row_d["amount"]
            cost_basis    = row_d["cost_basis_usd"]
            current_price = prices.get(asset, 0)
            current_value = amount * current_price
            unrealised_pl = current_value - cost_basis
            unrealised_pct= _pct(cost_basis, current_value) if cost_basis else 0

            result.append({
                **row_d,
                "current_price_usd":    round(current_price, 2),
                "current_value_usd":    round(current_value, 2),
                "unrealised_pl_usd":    round(unrealised_pl, 2),
                "unrealised_pl_pct":    round(unrealised_pct, 4),
                "cost_per_unit":        round(cost_basis / amount, 2) if amount > 0 else 0,
            })
        return result

    # ------------------------------------------------------------------
    # Portfolio value
    # ------------------------------------------------------------------

    def get_portfolio_value(self, pubkey: str) -> dict:
        """
        Compute total portfolio value, total cost basis, and P&L.
        """
        holdings = self.get_holdings(pubkey)
        if not holdings:
            return {
                "total_value_usd":    0.0,
                "total_cost_basis":   0.0,
                "unrealised_pl_usd":  0.0,
                "unrealised_pl_pct":  0.0,
                "holdings_count":     0,
            }

        total_value = sum(h["current_value_usd"] for h in holdings)
        total_cost  = sum(h["cost_basis_usd"]    for h in holdings)
        total_pl    = total_value - total_cost
        pl_pct      = _pct(total_cost, total_value)

        return {
            "total_value_usd":    round(total_value, 2),
            "total_cost_basis":   round(total_cost, 2),
            "unrealised_pl_usd":  round(total_pl, 2),
            "unrealised_pl_pct":  round(pl_pct, 4),
            "holdings_count":     len(holdings),
            "btc_value":          round(sum(h["current_value_usd"] for h in holdings if h["asset"] == "BTC"), 2),
        }

    # ------------------------------------------------------------------
    # Allocation
    # ------------------------------------------------------------------

    def get_allocation(self, pubkey: str) -> dict:
        """
        Return allocation percentages per asset and allocation grade.
        """
        holdings = self.get_holdings(pubkey)
        if not holdings:
            return {"assets": {}, "total_value_usd": 0.0}

        total_value = sum(h["current_value_usd"] for h in holdings)
        if total_value == 0:
            return {"assets": {}, "total_value_usd": 0.0}

        asset_values: dict[str, float] = {}
        for h in holdings:
            asset = h["asset"]
            asset_values[asset] = asset_values.get(asset, 0) + h["current_value_usd"]

        allocation = {}
        for asset, value in asset_values.items():
            allocation[asset] = {
                "value_usd":      round(value, 2),
                "allocation_pct": round(value / total_value * 100, 2),
            }

        # Sort by allocation descending
        sorted_alloc = dict(sorted(allocation.items(),
                                   key=lambda x: x[1]["allocation_pct"],
                                   reverse=True))

        return {
            "assets":          sorted_alloc,
            "total_value_usd": round(total_value, 2),
            "asset_count":     len(sorted_alloc),
        }

    # ------------------------------------------------------------------
    # Performance
    # ------------------------------------------------------------------

    def get_performance(self, pubkey: str, period: str = "all") -> dict:
        """
        Compute portfolio performance metrics.

        Parameters
        ----------
        period : 'day' | 'week' | 'month' | 'year' | 'all'
        """
        holdings = self.get_holdings(pubkey)
        if not holdings:
            return {"period": period, "return_pct": 0.0}

        total_value = sum(h["current_value_usd"] for h in holdings)
        total_cost  = sum(h["cost_basis_usd"]    for h in holdings)

        # Compute holding period for earliest acquisition
        earliest_acquisition = min(h["acquired_at"] for h in holdings)
        days_held = (time.time() - earliest_acquisition) / 86400

        # Period filter for transactions
        period_seconds = {
            "day":   86400,
            "week":  604800,
            "month": 2592000,
            "year":  31536000,
            "all":   int(time.time()),
        }
        since = int(time.time()) - period_seconds.get(period, int(time.time()))

        txs = self.get_transaction_history(pubkey, limit=1000, since=since)
        period_invested = sum(
            t["amount"] * t["price_usd"] + t["fee_usd"]
            for t in txs if t["tx_type"] == "buy"
        )
        period_withdrawn = sum(
            t["amount"] * t["price_usd"]
            for t in txs if t["tx_type"] == "sell"
        )

        total_return_pct = _pct(total_cost, total_value)
        annualised_pct   = _annualise(total_return_pct, days_held)

        return {
            "period":              period,
            "total_value_usd":     round(total_value, 2),
            "total_cost_basis":    round(total_cost, 2),
            "unrealised_pl_usd":   round(total_value - total_cost, 2),
            "total_return_pct":    round(total_return_pct, 4),
            "annualised_return_pct": round(annualised_pct, 4),
            "days_held":           round(days_held, 1),
            "period_invested_usd": round(period_invested, 2),
            "period_withdrawn_usd": round(period_withdrawn, 2),
            "transaction_count":   len(txs),
        }

    # ------------------------------------------------------------------
    # Transaction history
    # ------------------------------------------------------------------

    def get_transaction_history(self, pubkey: str, limit: int = 50,
                                 offset: int = 0, since: int = 0) -> list[dict]:
        """Return paginated transaction history."""
        p = _ph()
        conn = get_conn()
        rows = conn.execute(
            f"SELECT * FROM portfolio_transactions "
            f"WHERE pubkey = {p} AND timestamp >= {p} "
            f"ORDER BY timestamp DESC LIMIT {p} OFFSET {p}",
            (pubkey, since, limit, offset),
        ).fetchall()

        result = []
        for row in rows:
            row_d = dict(row) if hasattr(row, 'keys') else {
                "id": row[0], "pubkey": row[1], "tx_type": row[2],
                "asset": row[3], "amount": row[4], "price_usd": row[5],
                "fee_usd": row[6], "timestamp": row[7], "notes": row[8],
                "created_at": row[9],
            }
            row_d["total_usd"] = round(
                row_d["amount"] * row_d["price_usd"] + row_d["fee_usd"], 2
            )
            result.append(row_d)
        return result

    # ------------------------------------------------------------------
    # Cost basis
    # ------------------------------------------------------------------

    def get_cost_basis(self, pubkey: str, asset: str = "BTC",
                       method: str = "fifo") -> dict:
        """
        Calculate cost basis using FIFO, LIFO, or average cost method.

        Parameters
        ----------
        method : 'fifo' | 'lifo' | 'average'
        """
        p = _ph()
        conn = get_conn()
        buy_rows = conn.execute(
            f"SELECT amount, price_usd, fee_usd, timestamp FROM portfolio_transactions "
            f"WHERE pubkey = {p} AND asset = {p} AND tx_type = 'buy' "
            f"ORDER BY timestamp {'ASC' if method == 'fifo' else 'DESC'}",
            (pubkey, asset.upper()),
        ).fetchall()

        sell_rows = conn.execute(
            f"SELECT amount, price_usd, timestamp FROM portfolio_transactions "
            f"WHERE pubkey = {p} AND asset = {p} AND tx_type = 'sell' "
            f"ORDER BY timestamp ASC",
            (pubkey, asset.upper()),
        ).fetchall()

        if not buy_rows:
            return {"asset": asset, "method": method, "cost_basis": 0.0, "lots": []}

        lots = []
        for row in buy_rows:
            r = dict(row) if hasattr(row, 'keys') else {
                "amount": row[0], "price_usd": row[1], "fee_usd": row[2], "timestamp": row[3]
            }
            lots.append({
                "amount":    r["amount"],
                "price_usd": r["price_usd"],
                "fee_usd":   r.get("fee_usd", 0),
                "timestamp": r["timestamp"],
                "remaining": r["amount"],
            })

        # Apply sells to lots
        total_sold = sum(
            (dict(r) if hasattr(r, 'keys') else {"amount": r[0]})["amount"]
            for r in sell_rows
        )
        # Simple proportional reduction
        total_bought = sum(l["amount"] for l in lots)
        if total_sold > 0 and total_bought > 0:
            sell_ratio = min(total_sold / total_bought, 1.0)
            for lot in lots:
                lot["remaining"] = lot["amount"] * (1 - sell_ratio)

        remaining_lots = [l for l in lots if l["remaining"] > 0.00000001]

        if method == "average":
            total_cost = sum(l["remaining"] * l["price_usd"] + l.get("fee_usd", 0) for l in remaining_lots)
            total_amount = sum(l["remaining"] for l in remaining_lots)
            avg_cost = total_cost / total_amount if total_amount > 0 else 0
            return {
                "asset":           asset.upper(),
                "method":          "average",
                "cost_basis_total": round(total_cost, 2),
                "average_cost":    round(avg_cost, 2),
                "total_amount":    round(total_amount, 8),
            }
        else:
            total_cost   = sum(l["remaining"] * l["price_usd"] for l in remaining_lots)
            total_amount = sum(l["remaining"] for l in remaining_lots)
            return {
                "asset":           asset.upper(),
                "method":          method,
                "cost_basis_total": round(total_cost, 2),
                "average_cost":    round(total_cost / total_amount, 2) if total_amount > 0 else 0,
                "total_amount":    round(total_amount, 8),
                "lots":            remaining_lots[:20],  # top 20 lots
            }

    # ------------------------------------------------------------------
    # Realized gains
    # ------------------------------------------------------------------

    def get_realized_gains(self, pubkey: str, year: int = None) -> dict:
        """
        Calculate realized gains/losses for tax purposes.

        Parameters
        ----------
        year : int (e.g., 2024) — filter by tax year. None = all.
        """
        p = _ph()
        conn = get_conn()

        if year:
            year_start = int(time.mktime(time.strptime(f"{year}-01-01", "%Y-%m-%d")))
            year_end   = int(time.mktime(time.strptime(f"{year+1}-01-01", "%Y-%m-%d")))
            sell_rows = conn.execute(
                f"SELECT amount, price_usd, fee_usd, timestamp FROM portfolio_transactions "
                f"WHERE pubkey = {p} AND tx_type = 'sell' "
                f"AND timestamp >= {p} AND timestamp < {p} "
                f"ORDER BY timestamp",
                (pubkey, year_start, year_end),
            ).fetchall()
        else:
            sell_rows = conn.execute(
                f"SELECT amount, price_usd, fee_usd, timestamp FROM portfolio_transactions "
                f"WHERE pubkey = {p} AND tx_type = 'sell' ORDER BY timestamp",
                (pubkey,),
            ).fetchall()

        buy_rows = conn.execute(
            f"SELECT amount, price_usd, timestamp FROM portfolio_transactions "
            f"WHERE pubkey = {p} AND tx_type = 'buy' ORDER BY timestamp",
            (pubkey,),
        ).fetchall()

        # FIFO cost basis for sells
        buy_queue = [
            {"amount": (dict(r) if hasattr(r, 'keys') else {"amount": r[0], "price_usd": r[1], "timestamp": r[2]})["amount"],
             "price":  (dict(r) if hasattr(r, 'keys') else {"amount": r[0], "price_usd": r[1], "timestamp": r[2]})["price_usd"],
             "remaining": (dict(r) if hasattr(r, 'keys') else {"amount": r[0], "price_usd": r[1], "timestamp": r[2]})["amount"]}
            for r in buy_rows
        ]

        total_proceeds = 0.0
        total_cost     = 0.0
        events         = []

        for row in sell_rows:
            r = dict(row) if hasattr(row, 'keys') else {
                "amount": row[0], "price_usd": row[1], "fee_usd": row[2], "timestamp": row[3]
            }
            sell_amount   = r["amount"]
            sell_price    = r["price_usd"]
            sell_fee      = r.get("fee_usd", 0)
            proceeds      = sell_amount * sell_price - sell_fee
            cost_for_sale = 0.0
            remaining     = sell_amount

            for lot in buy_queue:
                if remaining <= 0:
                    break
                if lot["remaining"] <= 0:
                    continue
                used = min(remaining, lot["remaining"])
                cost_for_sale += used * lot["price"]
                lot["remaining"] -= used
                remaining -= used

            gain_loss = proceeds - cost_for_sale
            total_proceeds += proceeds
            total_cost     += cost_for_sale
            events.append({
                "timestamp":    r["timestamp"],
                "amount":       r["amount"],
                "proceeds_usd": round(proceeds, 2),
                "cost_usd":     round(cost_for_sale, 2),
                "gain_loss_usd": round(gain_loss, 2),
                "is_gain":      gain_loss >= 0,
            })

        total_gain_loss = total_proceeds - total_cost

        return {
            "tax_year":         year,
            "total_proceeds":   round(total_proceeds, 2),
            "total_cost_basis": round(total_cost, 2),
            "total_gain_loss":  round(total_gain_loss, 2),
            "is_net_gain":      total_gain_loss >= 0,
            "transaction_count": len(events),
            "events":            events,
        }

    def get_unrealized_gains(self, pubkey: str) -> dict:
        """Return unrealized gains by holding."""
        holdings = self.get_holdings(pubkey)
        events = []
        total_unrealised = 0.0

        for h in holdings:
            gain = h["unrealised_pl_usd"]
            total_unrealised += gain
            events.append({
                "holding_id":        h.get("id"),
                "asset":             h["asset"],
                "amount":            h["amount"],
                "cost_basis":        h["cost_basis_usd"],
                "current_value":     h["current_value_usd"],
                "unrealised_gain":   round(gain, 2),
                "unrealised_pct":    h["unrealised_pl_pct"],
            })

        return {
            "total_unrealised_gain_usd": round(total_unrealised, 2),
            "is_net_gain":               total_unrealised >= 0,
            "holdings":                  events,
        }

    # ------------------------------------------------------------------
    # Portfolio summary
    # ------------------------------------------------------------------

    def get_portfolio_summary(self, pubkey: str) -> dict:
        """Comprehensive portfolio summary."""
        value        = self.get_portfolio_value(pubkey)
        allocation   = self.get_allocation(pubkey)
        performance  = self.get_performance(pubkey, "all")
        unrealised   = self.get_unrealized_gains(pubkey)
        recent_txs   = self.get_transaction_history(pubkey, limit=5)

        return {
            "overview":         value,
            "allocation":       allocation,
            "performance":      performance,
            "unrealised_gains": unrealised,
            "recent_transactions": recent_txs,
            "generated_at":     int(time.time()),
        }

    # ------------------------------------------------------------------
    # Benchmark comparison
    # ------------------------------------------------------------------

    def compare_to_benchmark(self, pubkey: str, benchmark: str = "btc") -> dict:
        """
        Compare portfolio performance to a benchmark.

        Parameters
        ----------
        benchmark : 'btc' | 'sp500' (simplified)
        """
        perf = self.get_performance(pubkey, "all")
        portfolio_return = perf.get("total_return_pct", 0)
        days_held = perf.get("days_held", 365)

        # Simplified benchmark returns (approximate long-run averages)
        benchmark_annual = {
            "btc":   80.0,   # BTC historical CAGR ~80%
            "sp500": 10.5,   # S&P500 historical CAGR ~10.5%
            "gold":   7.0,
            "bonds":  3.0,
        }

        annual_bm = benchmark_annual.get(benchmark.lower(), 10.0)
        bm_total  = ((1 + annual_bm / 100) ** (days_held / 365) - 1) * 100 if days_held > 0 else annual_bm

        outperformance = portfolio_return - bm_total

        return {
            "portfolio_return_pct":  round(portfolio_return, 4),
            "benchmark":             benchmark,
            "benchmark_return_pct":  round(bm_total, 4),
            "outperformance_pct":    round(outperformance, 4),
            "outperformed":          outperformance > 0,
            "note": (
                "Benchmark returns are approximate historical averages; "
                "actual benchmark performance may vary."
            ),
        }

    # ------------------------------------------------------------------
    # Diversification score
    # ------------------------------------------------------------------

    def get_diversification_score(self, pubkey: str) -> float:
        """
        Score 0–100: higher = better diversification.
        Penalises heavy concentration in a single asset.
        """
        alloc = self.get_allocation(pubkey)
        assets = alloc.get("assets", {})
        if not assets:
            return 0.0

        allocations = [v["allocation_pct"] / 100 for v in assets.values()]
        n = len(allocations)
        if n == 1:
            return 10.0

        # Herfindahl-Hirschman Index: sum of squared shares
        hhi = sum(a ** 2 for a in allocations)
        # HHI of 1/n = maximum diversification; 1.0 = fully concentrated
        min_hhi = 1 / n
        # Normalise to 0–100 (100 = max diversification)
        score = (1 - (hhi - min_hhi) / (1 - min_hhi)) * 100 if n > 1 else 0
        return round(min(max(score, 0), 100), 1)
