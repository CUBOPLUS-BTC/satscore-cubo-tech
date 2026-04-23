"""Format conversion utilities for data exports.

Provides three formatter classes:
  - CSVFormatter  — plain-text CSV output
  - JSONFormatter — structured JSON with metadata envelope
  - HTMLFormatter — self-contained HTML report pages
"""

import csv
import io
import json
import time
import datetime
from typing import Any

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_APP_NAME = "Magma"
_APP_URL = "https://magma.app"


def _iso_now() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _ts_to_date(ts: int | None) -> str:
    if not ts:
        return ""
    return datetime.datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M UTC")


# ---------------------------------------------------------------------------
# CSVFormatter
# ---------------------------------------------------------------------------


class CSVFormatter:
    """Generate CSV strings from lists of row data.

    All methods return a UTF-8 string with CRLF line endings as
    recommended by RFC 4180.
    """

    # ------------------------------------------------------------------
    # Generic
    # ------------------------------------------------------------------

    def format_rows(self, headers: list[str], rows: list[list[Any]]) -> str:
        """Convert a header list and row matrix to a CSV string.

        Parameters
        ----------
        headers:
            Column names for the first row.
        rows:
            List of value lists.  Each inner list must have the same
            length as *headers*.

        Returns
        -------
        str  — UTF-8 CSV content.
        """
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\r\n")
        writer.writerow(headers)
        for row in rows:
            writer.writerow([str(v) if v is not None else "" for v in row])
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Deposits
    # ------------------------------------------------------------------

    def format_deposits(self, deposits: list[dict]) -> str:
        """Format a list of savings deposit records as CSV.

        Expected keys per deposit dict:
            id, amount_usd, btc_price, btc_amount, created_at

        Returns
        -------
        str  — CSV with a header row.
        """
        headers = [
            "ID",
            "Date (UTC)",
            "Amount (USD)",
            "BTC Price (USD)",
            "BTC Amount",
            "Sats",
            "Timestamp",
        ]
        rows = []
        for d in deposits:
            btc = float(d.get("btc_amount", 0) or 0)
            sats = int(btc * 100_000_000)
            rows.append([
                d.get("id", ""),
                _ts_to_date(d.get("created_at")),
                f"{float(d.get('amount_usd', 0) or 0):.2f}",
                f"{float(d.get('btc_price', 0) or 0):.2f}",
                f"{btc:.8f}",
                sats,
                d.get("created_at", ""),
            ])
        return self.format_rows(headers, rows)

    # ------------------------------------------------------------------
    # Achievements
    # ------------------------------------------------------------------

    def format_achievements(self, achievements: list[dict]) -> str:
        """Format a list of user achievement records as CSV.

        Expected keys per achievement dict:
            achievement_id, awarded_at, (optional) name, description

        Returns
        -------
        str  — CSV with a header row.
        """
        headers = ["Achievement ID", "Name", "Description", "Awarded At (UTC)", "Timestamp"]
        rows = []
        for a in achievements:
            rows.append([
                a.get("achievement_id", ""),
                a.get("name", a.get("achievement_id", "").replace("_", " ").title()),
                a.get("description", ""),
                _ts_to_date(a.get("awarded_at")),
                a.get("awarded_at", ""),
            ])
        return self.format_rows(headers, rows)

    # ------------------------------------------------------------------
    # Projections
    # ------------------------------------------------------------------

    def format_projections(self, projections: dict) -> str:
        """Flatten a projections dict (from SavingsProjector) into CSV.

        Expects the standard projection shape with a ``scenarios`` list
        or a ``yearly`` breakdown.  Produces one row per scenario or
        year.

        Returns
        -------
        str  — CSV with a header row.
        """
        scenarios = projections.get("scenarios", [])
        if scenarios:
            headers = [
                "Scenario",
                "Annual Return (%)",
                "Years",
                "Monthly Deposit (USD)",
                "Total Invested (USD)",
                "Final Value (USD)",
                "Final BTC",
                "Total Sats",
            ]
            rows = []
            for s in scenarios:
                rows.append([
                    s.get("label", ""),
                    s.get("annual_return_pct", ""),
                    s.get("years", ""),
                    f"{float(s.get('monthly_usd', 0) or 0):.2f}",
                    f"{float(s.get('total_invested_usd', 0) or 0):.2f}",
                    f"{float(s.get('final_value_usd', 0) or 0):.2f}",
                    f"{float(s.get('final_btc', 0) or 0):.8f}",
                    s.get("final_sats", ""),
                ])
            return self.format_rows(headers, rows)

        # Fallback: flat key-value export
        headers = ["Parameter", "Value"]
        rows = [[k, str(v)] for k, v in projections.items() if not isinstance(v, (dict, list))]
        return self.format_rows(headers, rows)


# ---------------------------------------------------------------------------
# JSONFormatter
# ---------------------------------------------------------------------------


class JSONFormatter:
    """Generate structured JSON strings with a consistent metadata envelope."""

    def format_report(self, data: dict, metadata: dict | None = None) -> str:
        """Wrap *data* in a standard metadata envelope and serialise.

        Parameters
        ----------
        data:
            The primary payload dict.
        metadata:
            Optional caller-supplied metadata (merged with defaults).

        Returns
        -------
        str  — Indented JSON string (2 spaces).
        """
        if metadata is None:
            metadata = {}
        envelope = {
            "meta": {
                "app": _APP_NAME,
                "generated_at": _iso_now(),
                "generated_at_ts": int(time.time()),
                "version": "1.0",
                **metadata,
            },
            "data": data,
        }
        return json.dumps(envelope, indent=2, ensure_ascii=False, default=str)

    def format_export(self, sections: list[dict]) -> str:
        """Serialise a multi-section export.

        Parameters
        ----------
        sections:
            List of dicts, each with at least ``"title"`` and
            ``"content"`` keys.

        Returns
        -------
        str  — Indented JSON string.
        """
        envelope = {
            "meta": {
                "app": _APP_NAME,
                "generated_at": _iso_now(),
                "generated_at_ts": int(time.time()),
                "section_count": len(sections),
                "version": "1.0",
            },
            "sections": sections,
        }
        return json.dumps(envelope, indent=2, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# HTMLFormatter
# ---------------------------------------------------------------------------

_HTML_STYLE = """
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0d0d0d;
    color: #e8e8e8;
    padding: 2rem;
    line-height: 1.6;
  }
  h1 { color: #ff6b00; font-size: 2rem; margin-bottom: 0.5rem; }
  h2 { color: #ff6b00; font-size: 1.25rem; margin: 2rem 0 0.75rem; border-bottom: 1px solid #333; padding-bottom: 0.4rem; }
  .meta { font-size: 0.85rem; color: #888; margin-bottom: 2rem; }
  .summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }
  .stat-card {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 1rem;
  }
  .stat-card .label { font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em; }
  .stat-card .value { font-size: 1.5rem; font-weight: 700; color: #ff6b00; margin-top: 0.25rem; }
  table { width: 100%; border-collapse: collapse; font-size: 0.9rem; margin-bottom: 1.5rem; }
  th { background: #1e1e1e; color: #ff6b00; text-align: left; padding: 0.6rem 0.8rem; font-weight: 600; border-bottom: 2px solid #333; }
  td { padding: 0.5rem 0.8rem; border-bottom: 1px solid #1e1e1e; }
  tr:hover td { background: #1a1a1a; }
  .chart-placeholder {
    background: #1a1a1a;
    border: 1px dashed #333;
    border-radius: 8px;
    padding: 2rem;
    text-align: center;
    color: #555;
    margin-bottom: 1.5rem;
  }
  footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #222; font-size: 0.8rem; color: #555; }
  .positive { color: #22c55e; }
  .negative { color: #ef4444; }
</style>
"""


class HTMLFormatter:
    """Generate self-contained HTML report pages.

    All output uses an inline ``<style>`` block so the file can be
    opened directly in a browser without external assets.
    """

    def format_report(self, title: str, sections: list[dict]) -> str:
        """Build a complete HTML document from a list of section dicts.

        Each section dict may have:
            type    ("table" | "summary" | "chart" | "text")
            title   (str)
            headers (list[str]) — for table sections
            rows    (list[list]) — for table sections
            stats   (dict)      — for summary sections
            data    (dict)      — for chart sections
            content (str)       — for text sections

        Parameters
        ----------
        title:
            Page ``<title>`` and main ``<h1>`` heading.
        sections:
            List of section dicts (see above).

        Returns
        -------
        str  — Complete HTML document.
        """
        body_parts = []
        for sec in sections:
            sec_type = sec.get("type", "text")
            sec_title = sec.get("title", "")
            if sec_title:
                body_parts.append(f"<h2>{_html_escape(sec_title)}</h2>")

            if sec_type == "table":
                body_parts.append(
                    self._render_table(sec.get("headers", []), sec.get("rows", []))
                )
            elif sec_type == "summary":
                body_parts.append(self._render_summary(sec.get("stats", {})))
            elif sec_type == "chart":
                body_parts.append(self._render_chart_placeholder(sec.get("data", {})))
            else:
                content = sec.get("content", "")
                if content:
                    body_parts.append(f"<p>{_html_escape(str(content))}</p>")

        generated = _iso_now()
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_html_escape(title)} — {_APP_NAME}</title>
  {_HTML_STYLE}
</head>
<body>
  <h1>{_html_escape(title)}</h1>
  <p class="meta">Generated by {_APP_NAME} &mdash; {generated}</p>
  {"".join(body_parts)}
  <footer>{_APP_NAME} &mdash; <a href="{_APP_URL}" style="color:#ff6b00;">{_APP_URL}</a></footer>
</body>
</html>"""
        return html

    def _render_table(self, headers: list[str], rows: list[list]) -> str:
        """Render an HTML ``<table>`` from headers and row data."""
        if not headers:
            return ""
        th_cells = "".join(f"<th>{_html_escape(str(h))}</th>" for h in headers)
        tr_rows = []
        for row in rows:
            td_cells = "".join(f"<td>{_html_escape(str(v) if v is not None else '')}</td>" for v in row)
            tr_rows.append(f"<tr>{td_cells}</tr>")
        return (
            f"<table><thead><tr>{th_cells}</tr></thead>"
            f"<tbody>{''.join(tr_rows)}</tbody></table>"
        )

    def _render_chart_placeholder(self, data: dict) -> str:
        """Render a placeholder block where a chart would be displayed."""
        chart_type = data.get("type", "line")
        label = data.get("label", "Chart")
        data_points = data.get("points", 0)
        return (
            f'<div class="chart-placeholder">'
            f"[{_html_escape(chart_type.upper())} CHART: {_html_escape(label)}"
            f" &mdash; {data_points} data points]"
            f"</div>"
        )

    def _render_summary(self, stats: dict) -> str:
        """Render a responsive grid of stat cards from a flat dict."""
        if not stats:
            return ""
        cards = []
        for key, val in stats.items():
            label = key.replace("_", " ").title()
            display_val = str(val) if val is not None else "—"
            cards.append(
                f'<div class="stat-card">'
                f'<div class="label">{_html_escape(label)}</div>'
                f'<div class="value">{_html_escape(display_val)}</div>'
                f"</div>"
            )
        return f'<div class="summary-grid">{"".join(cards)}</div>'


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _html_escape(text: str) -> str:
    """Minimal HTML entity escaping."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
    )
