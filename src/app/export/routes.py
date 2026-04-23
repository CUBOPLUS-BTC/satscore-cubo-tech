"""Export HTTP route handlers.

All handlers return ``(body_dict, status_code)`` tuples.  The HTTP
server serialises the dict to JSON and, where the export itself is
textual, embeds it in the response body or returns a download URL.

Endpoints:
  POST /export/data      -> handle_export_data(body, pubkey)
  GET  /export/deposits  -> handle_export_deposits(query, pubkey)
  POST /export/report    -> handle_export_report(body, pubkey)
"""

from .exporter import DataExporter
from ..validation import validate_pubkey

_exporter = DataExporter()

# Permitted export formats
_VALID_FORMATS = ("json", "csv", "html")


def _check_format(fmt: str | None) -> str:
    """Return a sanitised format string, defaulting to 'json'."""
    if not fmt or str(fmt).lower() not in _VALID_FORMATS:
        return "json"
    return str(fmt).lower()


def handle_export_data(body: dict, pubkey: str) -> tuple[dict, int]:
    """POST /export/data — trigger a full GDPR-style user data export.

    Request body:
      format (str): "json" | "csv" | "html"  (default "json")

    Returns the export content as a string inside ``{"export": ...}``.
    Requires authentication.
    """
    try:
        if not validate_pubkey(pubkey):
            return {"detail": "Invalid pubkey"}, 400

        fmt = _check_format(body.get("format", "json"))
        content = _exporter.export_user_data(pubkey, format=fmt)

        return {
            "format": fmt,
            "export": content,
            "size_bytes": len(content.encode("utf-8")),
        }, 200
    except Exception as exc:
        return {"detail": str(exc)}, 500


def handle_export_deposits(query: dict, pubkey: str) -> tuple[dict, int]:
    """GET /export/deposits — export deposit history with optional date range.

    Query parameters:
      format    (str):  "csv" | "json" | "html"  (default "csv")
      date_from (int):  Unix timestamp lower bound (default 0 = no limit)
      date_to   (int):  Unix timestamp upper bound (default 0 = now)

    Requires authentication.
    """
    try:
        if not validate_pubkey(pubkey):
            return {"detail": "Invalid pubkey"}, 400

        fmt = _check_format(query.get("format", "csv"))
        try:
            date_from = int(query.get("date_from", 0) or 0)
            date_to = int(query.get("date_to", 0) or 0)
        except (ValueError, TypeError):
            return {"detail": "date_from and date_to must be integers"}, 400

        content = _exporter.export_deposit_history(
            pubkey,
            format=fmt,
            date_from=date_from,
            date_to=date_to,
        )

        return {
            "format": fmt,
            "export": content,
            "size_bytes": len(content.encode("utf-8")),
        }, 200
    except Exception as exc:
        return {"detail": str(exc)}, 500


def handle_export_report(body: dict, pubkey: str) -> tuple[dict, int]:
    """POST /export/report — generate a structured report.

    The ``report_type`` field in the request body selects which report
    to generate:

      "savings"    — savings summary report (requires auth)
      "statement"  — monthly statement (requires auth)
      "remittance" — remittance comparison (public)
      "pension"    — pension projection (public)

    Request body fields vary by report type:
      All:         format (str)
      statement:   year (int), month (int 1-12)
      remittance:  amount_usd (float)
      pension:     monthly_usd (float), years (int), current_btc_price (float)

    Returns the report content embedded in ``{"report": ...}``.
    """
    try:
        report_type = str(body.get("report_type", "savings")).lower()
        fmt = _check_format(body.get("format", "json"))

        if report_type == "savings":
            if not validate_pubkey(pubkey):
                return {"detail": "Invalid pubkey"}, 400
            content = _exporter.export_savings_report(pubkey, format=fmt)

        elif report_type == "statement":
            if not validate_pubkey(pubkey):
                return {"detail": "Invalid pubkey"}, 400
            try:
                year = int(body.get("year", 0))
                month = int(body.get("month", 0))
            except (ValueError, TypeError):
                return {"detail": "year and month must be integers"}, 400
            if not (1 <= month <= 12):
                return {"detail": "month must be between 1 and 12"}, 400
            if year < 2020 or year > 2100:
                return {"detail": "year out of valid range"}, 400
            content = _exporter.generate_monthly_statement(pubkey, year, month, format=fmt)

        elif report_type == "remittance":
            try:
                amount_usd = float(body.get("amount_usd", 0))
            except (ValueError, TypeError):
                return {"detail": "amount_usd must be a number"}, 400
            if amount_usd <= 0:
                return {"detail": "amount_usd must be positive"}, 400
            content = _exporter.export_remittance_comparison(amount_usd, format=fmt)

        elif report_type == "pension":
            try:
                params = {
                    "monthly_usd": float(body.get("monthly_usd", 100)),
                    "years": int(body.get("years", 20)),
                    "current_btc_price": float(body.get("current_btc_price", 60000)),
                }
            except (ValueError, TypeError):
                return {"detail": "Invalid numeric parameter"}, 400
            if params["monthly_usd"] <= 0:
                return {"detail": "monthly_usd must be positive"}, 400
            if not (1 <= params["years"] <= 50):
                return {"detail": "years must be between 1 and 50"}, 400
            content = _exporter.export_pension_projection(params, format=fmt)

        else:
            return {
                "detail": f"Unknown report_type '{report_type}'. "
                          "Valid values: savings, statement, remittance, pension"
            }, 400

        return {
            "report_type": report_type,
            "format": fmt,
            "report": content,
            "size_bytes": len(content.encode("utf-8")),
        }, 200

    except Exception as exc:
        return {"detail": str(exc)}, 500
