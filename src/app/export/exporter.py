"""DataExporter — orchestrates data retrieval and format conversion.

Provides GDPR-style full exports, deposit history exports, savings
reports, remittance comparisons, pension projections, and monthly
statements.  All output is a string (CSV, JSON, or HTML) ready to be
sent as a file download response.
"""

import datetime
import json
import time
from ..database import get_conn, _is_postgres
from .formatters import CSVFormatter, JSONFormatter, HTMLFormatter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SATOSHIS_PER_BTC = 100_000_000
_SUPPORTED_FORMATS = ("csv", "json", "html")

# Standard remittance corridors and their typical fees (for comparison)
_REMITTANCE_PROVIDERS = [
    {"name": "Western Union", "fee_pct": 5.5, "fixed_fee_usd": 4.99},
    {"name": "MoneyGram",     "fee_pct": 4.0, "fixed_fee_usd": 3.99},
    {"name": "Remitly",       "fee_pct": 2.5, "fixed_fee_usd": 2.99},
    {"name": "Wise",          "fee_pct": 0.7, "fixed_fee_usd": 0.50},
    {"name": "Bitcoin (Lightning)", "fee_pct": 0.0, "fixed_fee_usd": 0.01},
]

# Conservative pension BTC appreciation scenarios (annual % gain over USD)
_PENSION_SCENARIOS = [
    {"label": "Conservative", "annual_btc_growth_pct": 20},
    {"label": "Moderate",     "annual_btc_growth_pct": 40},
    {"label": "Optimistic",   "annual_btc_growth_pct": 80},
]


def _ph() -> str:
    return "%s" if _is_postgres() else "?"


def _ts_to_iso(ts: int | None) -> str:
    if not ts:
        return ""
    return datetime.datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_format(fmt: str) -> str:
    fmt = str(fmt).lower().strip()
    if fmt not in _SUPPORTED_FORMATS:
        return "json"
    return fmt


def _row_get(row, key_or_idx, default=None):
    try:
        if hasattr(row, "keys"):
            return row[key_or_idx] if isinstance(key_or_idx, str) else list(row)[key_or_idx]
        return row[key_or_idx]
    except (IndexError, KeyError):
        return default


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class DataExporter:
    """Orchestrate data queries, transformations, and format serialisation."""

    def __init__(self) -> None:
        self._csv = CSVFormatter()
        self._json = JSONFormatter()
        self._html = HTMLFormatter()

    # ------------------------------------------------------------------
    # Full user data export (GDPR-style)
    # ------------------------------------------------------------------

    def export_user_data(self, pubkey: str, format: str = "json") -> str:
        """Export all data held for a user in the requested format.

        Includes: account info, preferences, savings goal, all deposits,
        all achievements, and analytics event counts.

        Parameters
        ----------
        pubkey:
            Target user's public key.
        format:
            One of ``"json"``, ``"csv"``, ``"html"`` (default ``"json"``).

        Returns
        -------
        str  — Serialised export content.
        """
        fmt = _validate_format(format)
        conn = get_conn()
        p = _ph()
        now = int(time.time())

        # --- Account ---
        user_row = conn.execute(
            f"SELECT pubkey, auth_method, created_at FROM users WHERE pubkey = {p}",
            (pubkey,),
        ).fetchone()
        account = {}
        if user_row:
            account = {
                "pubkey": _row_get(user_row, "pubkey" if hasattr(user_row, "keys") else 0, pubkey),
                "auth_method": _row_get(user_row, "auth_method" if hasattr(user_row, "keys") else 1, ""),
                "created_at": _row_get(user_row, "created_at" if hasattr(user_row, "keys") else 2, 0),
            }

        # --- Preferences ---
        pref_row = conn.execute(
            f"SELECT fee_alert_low, fee_alert_high, price_alerts, alerts_enabled, updated_at"
            f" FROM user_preferences WHERE pubkey = {p}",
            (pubkey,),
        ).fetchone()
        preferences = {}
        if pref_row:
            preferences = {
                "fee_alert_low": _row_get(pref_row, 0),
                "fee_alert_high": _row_get(pref_row, 1),
                "price_alerts": _row_get(pref_row, 2),
                "alerts_enabled": bool(_row_get(pref_row, 3)),
                "updated_at": _row_get(pref_row, 4),
            }

        # --- Savings goal ---
        goal_row = conn.execute(
            f"SELECT monthly_target_usd, target_years, created_at, updated_at"
            f" FROM savings_goals WHERE pubkey = {p}",
            (pubkey,),
        ).fetchone()
        goal = {}
        if goal_row:
            goal = {
                "monthly_target_usd": float(_row_get(goal_row, 0) or 0),
                "target_years": int(_row_get(goal_row, 1) or 0),
                "created_at": _row_get(goal_row, 2),
                "updated_at": _row_get(goal_row, 3),
            }

        # --- Deposits ---
        dep_rows = conn.execute(
            f"SELECT id, amount_usd, btc_price, btc_amount, created_at"
            f" FROM savings_deposits WHERE pubkey = {p} ORDER BY created_at",
            (pubkey,),
        ).fetchall()
        deposits = []
        for r in dep_rows:
            deposits.append({
                "id": _row_get(r, "id" if hasattr(r, "keys") else 0),
                "amount_usd": float(_row_get(r, "amount_usd" if hasattr(r, "keys") else 1) or 0),
                "btc_price": float(_row_get(r, "btc_price" if hasattr(r, "keys") else 2) or 0),
                "btc_amount": float(_row_get(r, "btc_amount" if hasattr(r, "keys") else 3) or 0),
                "created_at": _row_get(r, "created_at" if hasattr(r, "keys") else 4),
            })

        # --- Achievements ---
        ach_rows = conn.execute(
            f"SELECT achievement_id, awarded_at FROM user_achievements WHERE pubkey = {p}",
            (pubkey,),
        ).fetchall()
        achievements = []
        for r in ach_rows:
            achievements.append({
                "achievement_id": _row_get(r, "achievement_id" if hasattr(r, "keys") else 0, ""),
                "awarded_at": _row_get(r, "awarded_at" if hasattr(r, "keys") else 1),
            })

        # --- Analytics event count ---
        evt_row = conn.execute(
            f"SELECT COUNT(*) FROM analytics_events WHERE pubkey = {p}",
            (pubkey,),
        ).fetchone()
        event_count = int((_row_get(evt_row, 0) or 0)) if evt_row else 0

        data = {
            "account": account,
            "preferences": preferences,
            "savings_goal": goal,
            "deposits": deposits,
            "achievements": achievements,
            "analytics_event_count": event_count,
            "exported_at": _ts_to_iso(now),
        }

        if fmt == "json":
            return self._json.format_report(
                data,
                metadata={"type": "full_user_export", "pubkey_prefix": pubkey[:8] + "..."},
            )

        if fmt == "csv":
            # CSV can only represent one table cleanly — export deposits as primary
            sections = [
                f"# Magma Full User Export — {_ts_to_iso(now)}\n",
                f"# Pubkey: {pubkey}\n",
                f"# Total deposits: {len(deposits)}\n",
                f"# Total achievements: {len(achievements)}\n\n",
                "## DEPOSITS\n",
                self._csv.format_deposits(deposits),
                "\n## ACHIEVEMENTS\n",
                self._csv.format_achievements(achievements),
            ]
            return "".join(sections)

        # html
        total_btc = sum(d["btc_amount"] for d in deposits)
        total_usd = sum(d["amount_usd"] for d in deposits)
        sections = [
            {
                "type": "summary",
                "title": "Account Summary",
                "stats": {
                    "pubkey": pubkey[:16] + "...",
                    "auth_method": account.get("auth_method", ""),
                    "member_since": _ts_to_iso(account.get("created_at")),
                    "total_deposits": len(deposits),
                    "total_invested_usd": f"${total_usd:,.2f}",
                    "total_btc": f"{total_btc:.8f} BTC",
                    "total_sats": f"{int(total_btc * _SATOSHIS_PER_BTC):,}",
                    "achievements_unlocked": len(achievements),
                },
            },
            {
                "type": "table",
                "title": "Deposit History",
                "headers": ["Date", "Amount (USD)", "BTC Price", "BTC Amount", "Sats"],
                "rows": [
                    [
                        _ts_to_iso(d["created_at"]),
                        f"${d['amount_usd']:,.2f}",
                        f"${d['btc_price']:,.2f}",
                        f"{d['btc_amount']:.8f}",
                        f"{int(d['btc_amount'] * _SATOSHIS_PER_BTC):,}",
                    ]
                    for d in deposits
                ],
            },
            {
                "type": "table",
                "title": "Achievements",
                "headers": ["Achievement", "Awarded At"],
                "rows": [
                    [a["achievement_id"].replace("_", " ").title(), _ts_to_iso(a["awarded_at"])]
                    for a in achievements
                ],
            },
        ]
        return self._html.format_report(f"Full Export — {pubkey[:12]}...", sections)

    # ------------------------------------------------------------------
    # Deposit history export
    # ------------------------------------------------------------------

    def export_deposit_history(
        self,
        pubkey: str,
        format: str = "csv",
        date_from: int = 0,
        date_to: int = 0,
    ) -> str:
        """Export deposit history with optional date-range filtering.

        Parameters
        ----------
        pubkey:
            Target user's public key.
        format:
            ``"csv"``, ``"json"``, or ``"html"``.
        date_from:
            Unix timestamp lower bound (inclusive, 0 = no lower bound).
        date_to:
            Unix timestamp upper bound (inclusive, 0 = now).

        Returns
        -------
        str  — Serialised export content.
        """
        fmt = _validate_format(format)
        if date_to == 0:
            date_to = int(time.time())

        conn = get_conn()
        p = _ph()

        if date_from > 0:
            rows = conn.execute(
                f"SELECT id, amount_usd, btc_price, btc_amount, created_at"
                f" FROM savings_deposits WHERE pubkey = {p}"
                f" AND created_at >= {p} AND created_at <= {p}"
                f" ORDER BY created_at ASC",
                (pubkey, date_from, date_to),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT id, amount_usd, btc_price, btc_amount, created_at"
                f" FROM savings_deposits WHERE pubkey = {p}"
                f" AND created_at <= {p}"
                f" ORDER BY created_at ASC",
                (pubkey, date_to),
            ).fetchall()

        deposits = []
        for r in rows:
            deposits.append({
                "id": _row_get(r, "id" if hasattr(r, "keys") else 0),
                "amount_usd": float(_row_get(r, "amount_usd" if hasattr(r, "keys") else 1) or 0),
                "btc_price": float(_row_get(r, "btc_price" if hasattr(r, "keys") else 2) or 0),
                "btc_amount": float(_row_get(r, "btc_amount" if hasattr(r, "keys") else 3) or 0),
                "created_at": _row_get(r, "created_at" if hasattr(r, "keys") else 4),
            })

        if fmt == "csv":
            return self._csv.format_deposits(deposits)

        if fmt == "json":
            return self._json.format_report(
                {"deposits": deposits, "count": len(deposits)},
                metadata={"type": "deposit_history", "date_from": date_from, "date_to": date_to},
            )

        # html
        total_usd = sum(d["amount_usd"] for d in deposits)
        total_btc = sum(d["btc_amount"] for d in deposits)
        sections = [
            {
                "type": "summary",
                "title": "Deposit Summary",
                "stats": {
                    "deposits": len(deposits),
                    "total_usd": f"${total_usd:,.2f}",
                    "total_btc": f"{total_btc:.8f}",
                    "total_sats": f"{int(total_btc * _SATOSHIS_PER_BTC):,}",
                },
            },
            {
                "type": "table",
                "title": "All Deposits",
                "headers": ["Date (UTC)", "Amount (USD)", "BTC Price", "BTC", "Sats"],
                "rows": [
                    [
                        _ts_to_iso(d["created_at"]),
                        f"${d['amount_usd']:,.2f}",
                        f"${d['btc_price']:,.2f}",
                        f"{d['btc_amount']:.8f}",
                        f"{int(d['btc_amount'] * _SATOSHIS_PER_BTC):,}",
                    ]
                    for d in deposits
                ],
            },
        ]
        return self._html.format_report("Deposit History", sections)

    # ------------------------------------------------------------------
    # Savings report
    # ------------------------------------------------------------------

    def export_savings_report(self, pubkey: str, format: str = "json") -> str:
        """Generate a savings summary report.

        Includes total invested, current holdings, average buy price,
        goal progress, and the monthly bucketed aggregation.

        Returns
        -------
        str  — Serialised report content.
        """
        fmt = _validate_format(format)
        conn = get_conn()
        p = _ph()

        dep_rows = conn.execute(
            f"SELECT amount_usd, btc_price, btc_amount, created_at"
            f" FROM savings_deposits WHERE pubkey = {p} ORDER BY created_at",
            (pubkey,),
        ).fetchall()

        goal_row = conn.execute(
            f"SELECT monthly_target_usd, target_years FROM savings_goals WHERE pubkey = {p}",
            (pubkey,),
        ).fetchone()

        total_usd = 0.0
        total_btc = 0.0
        prices = []
        monthly: dict[str, dict] = {}

        for r in dep_rows:
            usd = float(_row_get(r, "amount_usd" if hasattr(r, "keys") else 0) or 0)
            price = float(_row_get(r, "btc_price" if hasattr(r, "keys") else 1) or 0)
            btc = float(_row_get(r, "btc_amount" if hasattr(r, "keys") else 2) or 0)
            ts = int(_row_get(r, "created_at" if hasattr(r, "keys") else 3) or 0)
            total_usd += usd
            total_btc += btc
            if price > 0:
                prices.append(price)
            month = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m")
            if month not in monthly:
                monthly[month] = {"usd": 0.0, "btc": 0.0, "count": 0}
            monthly[month]["usd"] += usd
            monthly[month]["btc"] += btc
            monthly[month]["count"] += 1

        avg_buy = total_usd / total_btc if total_btc > 0 else 0.0
        current_price = prices[-1] if prices else 0.0
        current_value = total_btc * current_price

        monthly_target = 0.0
        target_years = 0
        if goal_row:
            monthly_target = float(_row_get(goal_row, 0) or 0)
            target_years = int(_row_get(goal_row, 1) or 0)

        months_active = len(monthly)
        on_track_pct = (
            (total_usd / (monthly_target * months_active) * 100)
            if (monthly_target > 0 and months_active > 0)
            else 0.0
        )

        monthly_rows = [
            {
                "month": m,
                "deposits": monthly[m]["count"],
                "usd": round(monthly[m]["usd"], 2),
                "btc": round(monthly[m]["btc"], 8),
            }
            for m in sorted(monthly.keys())
        ]

        data = {
            "total_invested_usd": round(total_usd, 2),
            "total_btc": round(total_btc, 8),
            "total_sats": int(total_btc * _SATOSHIS_PER_BTC),
            "avg_buy_price_usd": round(avg_buy, 2),
            "current_price_usd": round(current_price, 2),
            "current_value_usd": round(current_value, 2),
            "unrealised_pnl_usd": round(current_value - total_usd, 2),
            "deposit_count": len(dep_rows),
            "goal_monthly_target_usd": round(monthly_target, 2),
            "goal_target_years": target_years,
            "on_track_pct": round(on_track_pct, 1),
            "monthly_breakdown": monthly_rows,
        }

        if fmt == "json":
            return self._json.format_report(data, metadata={"type": "savings_report"})

        if fmt == "csv":
            headers = ["Month", "Deposits", "USD Invested", "BTC Acquired"]
            rows = [[m["month"], m["deposits"], m["usd"], m["btc"]] for m in monthly_rows]
            return self._csv.format_rows(headers, rows)

        # html
        pnl = data["unrealised_pnl_usd"]
        pnl_class = "positive" if pnl >= 0 else "negative"
        sections = [
            {
                "type": "summary",
                "title": "Savings Overview",
                "stats": {
                    "total_invested": f"${data['total_invested_usd']:,.2f}",
                    "total_btc": f"{data['total_btc']:.8f}",
                    "total_sats": f"{data['total_sats']:,}",
                    "avg_buy_price": f"${data['avg_buy_price_usd']:,.2f}",
                    "current_value": f"${data['current_value_usd']:,.2f}",
                    "unrealised_pnl": f"${pnl:+,.2f}",
                    "on_track": f"{data['on_track_pct']:.1f}%",
                },
            },
            {
                "type": "table",
                "title": "Monthly Breakdown",
                "headers": ["Month", "Deposits", "USD Invested", "BTC Acquired"],
                "rows": [[m["month"], m["deposits"], f"${m['usd']:,.2f}", f"{m['btc']:.8f}"] for m in monthly_rows],
            },
        ]
        return self._html.format_report("Savings Report", sections)

    # ------------------------------------------------------------------
    # Remittance comparison
    # ------------------------------------------------------------------

    def export_remittance_comparison(self, amount: float, format: str = "json") -> str:
        """Generate a cost comparison for sending *amount* USD via various providers.

        Parameters
        ----------
        amount:
            Amount in USD to remit.
        format:
            Output format.

        Returns
        -------
        str  — Serialised comparison.
        """
        fmt = _validate_format(format)
        comparisons = []
        for provider in _REMITTANCE_PROVIDERS:
            fee_usd = provider["fixed_fee_usd"] + amount * provider["fee_pct"] / 100
            recipient_gets = amount - fee_usd
            total_cost_pct = fee_usd / amount * 100 if amount > 0 else 0.0
            comparisons.append({
                "provider": provider["name"],
                "fee_pct": provider["fee_pct"],
                "fixed_fee_usd": provider["fixed_fee_usd"],
                "total_fee_usd": round(fee_usd, 2),
                "recipient_gets_usd": round(recipient_gets, 2),
                "total_cost_pct": round(total_cost_pct, 2),
            })
        comparisons.sort(key=lambda x: x["total_fee_usd"])

        data = {
            "send_amount_usd": round(amount, 2),
            "providers": comparisons,
            "cheapest": comparisons[0]["provider"] if comparisons else None,
            "savings_vs_western_union_usd": round(
                next((c["total_fee_usd"] for c in comparisons if "Western Union" in c["provider"]), 0)
                - comparisons[0]["total_fee_usd"],
                2,
            ),
        }

        if fmt == "json":
            return self._json.format_report(data, metadata={"type": "remittance_comparison"})

        if fmt == "csv":
            headers = ["Provider", "Fee %", "Fixed Fee (USD)", "Total Fee (USD)", "Recipient Gets (USD)"]
            rows = [[c["provider"], c["fee_pct"], c["fixed_fee_usd"], c["total_fee_usd"], c["recipient_gets_usd"]] for c in comparisons]
            return self._csv.format_rows(headers, rows)

        sections = [
            {
                "type": "summary",
                "title": "Send Amount",
                "stats": {"amount_usd": f"${amount:,.2f}", "cheapest_option": data["cheapest"]},
            },
            {
                "type": "table",
                "title": "Provider Comparison",
                "headers": ["Provider", "Fee %", "Fixed (USD)", "Total Fee (USD)", "Recipient Gets"],
                "rows": [
                    [c["provider"], f"{c['fee_pct']}%", f"${c['fixed_fee_usd']:.2f}", f"${c['total_fee_usd']:.2f}", f"${c['recipient_gets_usd']:,.2f}"]
                    for c in comparisons
                ],
            },
        ]
        return self._html.format_report("Remittance Comparison", sections)

    # ------------------------------------------------------------------
    # Pension projection
    # ------------------------------------------------------------------

    def export_pension_projection(self, params: dict, format: str = "json") -> str:
        """Generate a Bitcoin pension projection export.

        Parameters
        ----------
        params:
            monthly_usd (float), years (int), current_btc_price (float)
        format:
            Output format.

        Returns
        -------
        str  — Serialised projection.
        """
        fmt = _validate_format(format)
        monthly_usd = float(params.get("monthly_usd", 100))
        years = int(params.get("years", 20))
        btc_price = float(params.get("current_btc_price", 60000))
        total_invested = monthly_usd * 12 * years

        scenario_results = []
        for sc in _PENSION_SCENARIOS:
            rate = sc["annual_btc_growth_pct"] / 100
            total_btc = 0.0
            for y in range(years):
                future_price = btc_price * ((1 + rate) ** y)
                monthly_btc = (monthly_usd / future_price) if future_price > 0 else 0
                total_btc += monthly_btc * 12
            final_price = btc_price * ((1 + rate) ** years)
            final_value = total_btc * final_price
            scenario_results.append({
                "label": sc["label"],
                "annual_growth_pct": sc["annual_btc_growth_pct"],
                "total_btc": round(total_btc, 8),
                "total_sats": int(total_btc * _SATOSHIS_PER_BTC),
                "final_btc_price_usd": round(final_price, 2),
                "final_value_usd": round(final_value, 2),
                "roi_pct": round((final_value - total_invested) / total_invested * 100, 1) if total_invested > 0 else 0,
            })

        data = {
            "monthly_deposit_usd": monthly_usd,
            "years": years,
            "total_invested_usd": round(total_invested, 2),
            "current_btc_price": btc_price,
            "scenarios": scenario_results,
        }

        if fmt == "json":
            return self._json.format_report(data, metadata={"type": "pension_projection"})

        if fmt == "csv":
            return self._csv.format_projections(data)

        sections = [
            {
                "type": "summary",
                "title": "Projection Parameters",
                "stats": {
                    "monthly_deposit": f"${monthly_usd:,.2f}",
                    "years": years,
                    "total_invested": f"${total_invested:,.2f}",
                    "current_btc_price": f"${btc_price:,.2f}",
                },
            },
            {
                "type": "table",
                "title": "Scenarios",
                "headers": ["Scenario", "Annual Growth", "Total BTC", "Final Value (USD)", "ROI %"],
                "rows": [
                    [s["label"], f"{s['annual_growth_pct']}%", f"{s['total_btc']:.8f}", f"${s['final_value_usd']:,.2f}", f"{s['roi_pct']:.1f}%"]
                    for s in scenario_results
                ],
            },
        ]
        return self._html.format_report("Pension Projection", sections)

    # ------------------------------------------------------------------
    # Monthly statement
    # ------------------------------------------------------------------

    def generate_monthly_statement(
        self,
        pubkey: str,
        year: int,
        month: int,
        format: str = "pdf",
    ) -> str:
        """Generate a monthly account statement for a given year/month.

        Parameters
        ----------
        pubkey:
            Target user's public key.
        year:
            Calendar year (e.g. 2025).
        month:
            Calendar month 1–12.
        format:
            ``"json"``, ``"csv"``, or ``"html"`` (``"pdf"`` is aliased
            to ``"html"`` since PDF rendering requires a browser engine).

        Returns
        -------
        str  — Serialised statement.
        """
        # pdf → html fallback (actual PDF rendering is front-end's job)
        if str(format).lower() == "pdf":
            format = "html"
        fmt = _validate_format(format)

        import calendar
        month_start_dt = datetime.datetime(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        month_end_dt = datetime.datetime(year, month, last_day, 23, 59, 59)
        month_start_ts = int(month_start_dt.timestamp())
        month_end_ts = int(month_end_dt.timestamp())

        conn = get_conn()
        p = _ph()
        rows = conn.execute(
            f"SELECT id, amount_usd, btc_price, btc_amount, created_at"
            f" FROM savings_deposits WHERE pubkey = {p}"
            f" AND created_at >= {p} AND created_at <= {p}"
            f" ORDER BY created_at ASC",
            (pubkey, month_start_ts, month_end_ts),
        ).fetchall()

        deposits = []
        for r in rows:
            deposits.append({
                "id": _row_get(r, "id" if hasattr(r, "keys") else 0),
                "amount_usd": float(_row_get(r, "amount_usd" if hasattr(r, "keys") else 1) or 0),
                "btc_price": float(_row_get(r, "btc_price" if hasattr(r, "keys") else 2) or 0),
                "btc_amount": float(_row_get(r, "btc_amount" if hasattr(r, "keys") else 3) or 0),
                "created_at": _row_get(r, "created_at" if hasattr(r, "keys") else 4),
            })

        total_usd = sum(d["amount_usd"] for d in deposits)
        total_btc = sum(d["btc_amount"] for d in deposits)
        avg_price = total_usd / total_btc if total_btc > 0 else 0.0
        month_label = month_start_dt.strftime("%B %Y")

        data = {
            "statement_month": month_label,
            "year": year,
            "month": month,
            "pubkey_prefix": pubkey[:12] + "...",
            "deposit_count": len(deposits),
            "total_usd": round(total_usd, 2),
            "total_btc": round(total_btc, 8),
            "total_sats": int(total_btc * _SATOSHIS_PER_BTC),
            "avg_btc_price": round(avg_price, 2),
            "deposits": deposits,
        }

        if fmt == "json":
            return self._json.format_report(data, metadata={"type": "monthly_statement", "month": month_label})

        if fmt == "csv":
            return self._csv.format_deposits(deposits)

        sections = [
            {
                "type": "summary",
                "title": f"Statement for {month_label}",
                "stats": {
                    "deposits": len(deposits),
                    "total_usd": f"${total_usd:,.2f}",
                    "total_btc": f"{total_btc:.8f}",
                    "sats_accumulated": f"{int(total_btc * _SATOSHIS_PER_BTC):,}",
                    "avg_btc_price": f"${avg_price:,.2f}",
                },
            },
            {
                "type": "table",
                "title": "Deposit Details",
                "headers": ["Date (UTC)", "USD", "BTC Price", "BTC", "Sats"],
                "rows": [
                    [
                        _ts_to_iso(d["created_at"]),
                        f"${d['amount_usd']:,.2f}",
                        f"${d['btc_price']:,.2f}",
                        f"{d['btc_amount']:.8f}",
                        f"{int(d['btc_amount'] * _SATOSHIS_PER_BTC):,}",
                    ]
                    for d in deposits
                ],
            },
        ]
        return self._html.format_report(f"Monthly Statement — {month_label}", sections)
