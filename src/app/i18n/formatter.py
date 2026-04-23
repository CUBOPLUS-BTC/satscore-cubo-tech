"""
Locale-aware formatting for Magma Bitcoin app.
Formats currency, Bitcoin amounts, dates, and notification messages.
Pure Python stdlib — no third-party dependencies.
"""

import time
import math
from typing import Optional


# ---------------------------------------------------------------------------
# Locale format data
# ---------------------------------------------------------------------------

_LOCALE_FORMATS = {
    "en": {
        "thousands": ",",
        "decimal":   ".",
        "currency_prefix": "$",
        "currency_suffix": "",
        "date": "%m/%d/%Y",
        "datetime": "%m/%d/%Y %I:%M %p",
    },
    "es": {
        "thousands": ".",
        "decimal":   ",",
        "currency_prefix": "$",
        "currency_suffix": "",
        "date": "%d/%m/%Y",
        "datetime": "%d/%m/%Y %H:%M",
    },
    "de": {
        "thousands": ".",
        "decimal":   ",",
        "currency_prefix": "",
        "currency_suffix": " €",
        "date": "%d.%m.%Y",
        "datetime": "%d.%m.%Y %H:%M",
    },
    "fr": {
        "thousands": "\u202f",  # narrow no-break space
        "decimal":   ",",
        "currency_prefix": "",
        "currency_suffix": "\u00a0€",
        "date": "%d/%m/%Y",
        "datetime": "%d/%m/%Y %H:%M",
    },
}

_CURRENCY_SYMBOLS = {
    "USD": "$",  "EUR": "€",  "GBP": "£",  "JPY": "¥",
    "BTC": "₿",  "MXN": "$",  "BRL": "R$", "CRC": "₡",
    "GTQ": "Q",  "HNL": "L",  "NIO": "C$", "PEN": "S/",
    "COP": "$",  "ARS": "$",  "CLP": "$",  "BOB": "Bs",
}

_RELATIVE_LABELS_EN = {
    "just_now":    "Just now",
    "minute":      "{n} minute ago",
    "minutes":     "{n} minutes ago",
    "hour":        "{n} hour ago",
    "hours":       "{n} hours ago",
    "day":         "{n} day ago",
    "days":        "{n} days ago",
    "week":        "{n} week ago",
    "weeks":       "{n} weeks ago",
    "month":       "{n} month ago",
    "months":      "{n} months ago",
    "year":        "{n} year ago",
    "years":       "{n} years ago",
}

_RELATIVE_LABELS_ES = {
    "just_now":    "Justo ahora",
    "minute":      "hace {n} minuto",
    "minutes":     "hace {n} minutos",
    "hour":        "hace {n} hora",
    "hours":       "hace {n} horas",
    "day":         "hace {n} día",
    "days":        "hace {n} días",
    "week":        "hace {n} semana",
    "weeks":       "hace {n} semanas",
    "month":       "hace {n} mes",
    "months":      "hace {n} meses",
    "year":        "hace {n} año",
    "years":       "hace {n} años",
}

_DURATION_LABELS_EN = {
    "second": "second", "seconds": "seconds",
    "minute": "minute", "minutes": "minutes",
    "hour":   "hour",   "hours":   "hours",
    "day":    "day",    "days":    "days",
}

_DURATION_LABELS_ES = {
    "second": "segundo", "seconds": "segundos",
    "minute": "minuto",  "minutes": "minutos",
    "hour":   "hora",    "hours":   "horas",
    "day":    "día",     "days":    "días",
}


def _get_fmt(locale: str) -> dict:
    base = locale.lower().split("_")[0].split("-")[0]
    return _LOCALE_FORMATS.get(base, _LOCALE_FORMATS["en"])


def _format_number_str(value: float, decimals: int, fmt: dict) -> str:
    """Format a float with locale-specific thousands/decimal separators."""
    # Format with standard dot decimal first
    if decimals == 0:
        integer_part = str(abs(int(round(value))))
        decimal_part = ""
    else:
        formatted = f"{abs(value):.{decimals}f}"
        parts = formatted.split(".")
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else ""

    # Apply thousands separator
    grouped = []
    for i, ch in enumerate(reversed(integer_part)):
        if i > 0 and i % 3 == 0:
            grouped.append(fmt["thousands"])
        grouped.append(ch)
    integer_formatted = "".join(reversed(grouped))

    sign = "-" if value < 0 else ""

    if decimal_part:
        return f"{sign}{integer_formatted}{fmt['decimal']}{decimal_part}"
    return f"{sign}{integer_formatted}"


# ---------------------------------------------------------------------------
# NumberFormatter
# ---------------------------------------------------------------------------

class NumberFormatter:
    """
    Locale-aware number and currency formatting.
    """

    @staticmethod
    def format_currency(
        amount: float,
        currency: str = "USD",
        locale: str = "en",
        decimals: int = 2,
    ) -> str:
        """
        Format a currency amount with locale-appropriate separators and symbol.

        Examples:
          en, USD: "$1,234.56"
          es, USD: "$1.234,56"
          de, EUR: "1.234,56 €"
        """
        fmt = _get_fmt(locale)
        symbol = _CURRENCY_SYMBOLS.get(currency.upper(), currency)
        number_str = _format_number_str(float(amount), decimals, fmt)

        prefix = symbol if fmt["currency_prefix"] else fmt["currency_prefix"]
        suffix = fmt["currency_suffix"]

        if fmt["currency_prefix"]:
            return f"{symbol}{number_str}{suffix}"
        return f"{number_str}{suffix.replace('€', symbol).strip()}"

    @staticmethod
    def format_bitcoin(amount: float, locale: str = "en") -> str:
        """
        Format a Bitcoin amount with 8 decimal places and the ₿ symbol.
        Always uses period decimal separator regardless of locale.

        Example: "₿0.01234567"
        """
        return f"₿{abs(amount):.8f}"

    @staticmethod
    def format_sats(amount: int, locale: str = "en") -> str:
        """
        Format a satoshi amount with thousands separators.

        Examples:
          en: "1,234,567 sats"
          es: "1.234.567 sats"
        """
        fmt = _get_fmt(locale)
        number_str = _format_number_str(float(int(amount)), 0, fmt)
        return f"{number_str} sats"

    @staticmethod
    def format_percentage(value: float, locale: str = "en", decimals: int = 2) -> str:
        """
        Format a percentage value.

        Examples:
          en: "12.34%"
          de: "12,34 %"
        """
        fmt = _get_fmt(locale)
        number_str = _format_number_str(float(value), decimals, fmt)
        return f"{number_str}%"

    @staticmethod
    def format_number(value: float, locale: str = "en", decimals: int = 2) -> str:
        """
        Format a plain number with locale-appropriate separators.
        """
        fmt = _get_fmt(locale)
        return _format_number_str(float(value), decimals, fmt)

    @staticmethod
    def format_compact(value: float, locale: str = "en") -> str:
        """
        Format a large number in compact form.

        Examples:
          1_234_567 → "1.2M"
          9_876 → "9.9K"
        """
        abs_val = abs(value)
        sign = "-" if value < 0 else ""

        if abs_val >= 1_000_000_000:
            compact = f"{abs_val / 1_000_000_000:.1f}B"
        elif abs_val >= 1_000_000:
            compact = f"{abs_val / 1_000_000:.1f}M"
        elif abs_val >= 1_000:
            compact = f"{abs_val / 1_000:.1f}K"
        else:
            compact = f"{abs_val:.0f}"

        return f"{sign}{compact}"


# ---------------------------------------------------------------------------
# DateFormatter
# ---------------------------------------------------------------------------

class DateFormatter:
    """
    Locale-aware date and time formatting.
    All timestamps are assumed to be Unix UTC timestamps (integers).
    """

    @staticmethod
    def format_date(timestamp: int, locale: str = "en", fmt: str = None) -> str:
        """
        Format a Unix timestamp as a locale-appropriate date string.

        ``fmt`` overrides the locale default (strftime format string).
        """
        import datetime
        try:
            dt = datetime.datetime.utcfromtimestamp(int(timestamp))
        except (ValueError, OSError, OverflowError):
            return "—"

        locale_fmt = _get_fmt(locale)
        format_str = fmt or locale_fmt["date"]
        return dt.strftime(format_str)

    @staticmethod
    def format_datetime(timestamp: int, locale: str = "en") -> str:
        """Format a Unix timestamp as a full locale-appropriate datetime string."""
        import datetime
        try:
            dt = datetime.datetime.utcfromtimestamp(int(timestamp))
        except (ValueError, OSError, OverflowError):
            return "—"

        locale_fmt = _get_fmt(locale)
        return dt.strftime(locale_fmt.get("datetime", "%Y-%m-%d %H:%M"))

    @staticmethod
    def format_relative(timestamp: int, locale: str = "en") -> str:
        """
        Format a Unix timestamp as a relative time string.

        Examples:
          en: "3 hours ago", "Just now"
          es: "hace 3 horas", "Justo ahora"
        """
        now = int(time.time())
        diff = now - int(timestamp)

        if diff < 0:
            diff = 0

        labels = _RELATIVE_LABELS_ES if locale.lower().startswith("es") else _RELATIVE_LABELS_EN

        def fmt(key_singular: str, key_plural: str, n: int) -> str:
            key = key_singular if n == 1 else key_plural
            return labels[key].replace("{n}", str(n))

        if diff < 60:
            return labels["just_now"]
        if diff < 3600:
            n = diff // 60
            return fmt("minute", "minutes", n)
        if diff < 86400:
            n = diff // 3600
            return fmt("hour", "hours", n)
        if diff < 7 * 86400:
            n = diff // 86400
            return fmt("day", "days", n)
        if diff < 30 * 86400:
            n = diff // (7 * 86400)
            return fmt("week", "weeks", n)
        if diff < 365 * 86400:
            n = diff // (30 * 86400)
            return fmt("month", "months", n)

        n = diff // (365 * 86400)
        return fmt("year", "years", n)

    @staticmethod
    def format_duration(seconds: int, locale: str = "en") -> str:
        """
        Format a duration in seconds as a human-readable string.

        Examples:
          en: "3 days, 2 hours, 15 minutes"
          es: "3 días, 2 horas, 15 minutos"
        """
        seconds = max(0, int(seconds))
        labels = _DURATION_LABELS_ES if locale.lower().startswith("es") else _DURATION_LABELS_EN

        parts = []
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, secs = divmod(remainder, 60)

        if days:
            key = "day" if days == 1 else "days"
            parts.append(f"{days} {labels[key]}")
        if hours:
            key = "hour" if hours == 1 else "hours"
            parts.append(f"{hours} {labels[key]}")
        if minutes:
            key = "minute" if minutes == 1 else "minutes"
            parts.append(f"{minutes} {labels[key]}")
        if not parts and secs:
            key = "second" if secs == 1 else "seconds"
            parts.append(f"{secs} {labels[key]}")

        return ", ".join(parts) or f"0 {labels['seconds']}"

    @staticmethod
    def format_date_range(
        from_ts: int,
        to_ts: int,
        locale: str = "en",
    ) -> str:
        """
        Format a date range as a human-readable string.

        Examples:
          en: "01/15/2025 – 02/15/2025"
          es: "15/01/2025 – 15/02/2025"
        """
        from_str = DateFormatter.format_date(from_ts, locale)
        to_str   = DateFormatter.format_date(to_ts, locale)
        return f"{from_str} – {to_str}"

    @staticmethod
    def format_month(timestamp: int, locale: str = "en") -> str:
        """Format a timestamp as Month YYYY."""
        import datetime
        months_en = ["January", "February", "March", "April", "May", "June",
                     "July", "August", "September", "October", "November", "December"]
        months_es = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                     "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

        try:
            dt = datetime.datetime.utcfromtimestamp(int(timestamp))
            months = months_es if locale.lower().startswith("es") else months_en
            return f"{months[dt.month - 1]} {dt.year}"
        except Exception:
            return "—"


# ---------------------------------------------------------------------------
# MessageFormatter
# ---------------------------------------------------------------------------

class MessageFormatter:
    """
    High-level message formatting for notifications, achievements, alerts, and errors.
    Uses the Translator internally for all text lookups.
    """

    def __init__(self, locale: str = "en") -> None:
        from .translator import Translator
        self._t = Translator(default_locale=locale)
        self._default_locale = locale
        self._numbers = NumberFormatter()
        self._dates = DateFormatter()

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    def format_notification(
        self,
        template_key: str,
        locale: str = None,
        **data,
    ) -> str:
        """
        Format a notification message from a template key.

        Example::

            formatter.format_notification(
                "notification.deposit.body",
                locale="es",
                amount="$50",
                total="$250",
            )
        """
        return self._t.translate(template_key, locale=locale or self._default_locale, **data)

    def format_notification_full(
        self,
        notification_type: str,
        locale: str = None,
        **data,
    ) -> dict:
        """
        Return both title and body for a notification type.

        Example: format_notification_full("deposit", locale="es", amount="$50", total="$250")
        """
        loc = locale or self._default_locale
        return {
            "title": self._t.translate(f"notification.{notification_type}.title", locale=loc, **data),
            "body":  self._t.translate(f"notification.{notification_type}.body",  locale=loc, **data),
        }

    # ------------------------------------------------------------------
    # Achievements
    # ------------------------------------------------------------------

    def format_achievement(
        self,
        achievement_id: str,
        locale: str = None,
    ) -> dict:
        """
        Return the localized name and description for an achievement.

        Example::

            formatter.format_achievement("first_deposit", locale="es")
            # → {"name": "Primeros Pasos", "desc": "Realizó su primer depósito…"}
        """
        loc = locale or self._default_locale
        return {
            "id":   achievement_id,
            "name": self._t.translate(f"achievement.{achievement_id}.name", locale=loc),
            "desc": self._t.translate(f"achievement.{achievement_id}.desc", locale=loc),
        }

    def format_achievement_earned(
        self,
        achievement_id: str,
        locale: str = None,
    ) -> str:
        """Return the 'achievement earned' toast message."""
        loc = locale or self._default_locale
        name = self._t.translate(f"achievement.{achievement_id}.name", locale=loc)
        return self._t.translate("achievements.earned", locale=loc, name=name)

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    def format_alert(
        self,
        alert_type: str,
        locale: str = None,
        **data,
    ) -> dict:
        """
        Return a structured alert message dict with title and body.

        ``alert_type`` maps to notification.{alert_type}.title/body keys.
        """
        loc = locale or self._default_locale
        title_key = f"alerts.{alert_type}.title" if self._t.has_translation(f"alerts.{alert_type}.title", loc) \
            else f"notification.{alert_type}.title"
        body_key  = f"alerts.{alert_type}"

        return {
            "alert_type": alert_type,
            "title":      self._t.translate(title_key, locale=loc, **data),
            "body":       self._t.translate(body_key, locale=loc, **data),
        }

    # ------------------------------------------------------------------
    # Errors
    # ------------------------------------------------------------------

    def format_error(
        self,
        error_code: str,
        locale: str = None,
        **details,
    ) -> dict:
        """
        Return a structured error response dict.

        ``error_code`` maps to an "error.*" translation key.
        """
        loc = locale or self._default_locale
        message = self._t.translate(f"error.{error_code}", locale=loc, **details)
        if message == f"error.{error_code}":
            message = self._t.translate("error.internal", locale=loc)

        return {
            "error":   error_code,
            "message": message,
            "locale":  loc,
        }

    # ------------------------------------------------------------------
    # Savings / Finance messages
    # ------------------------------------------------------------------

    def format_savings_summary(
        self,
        total_usd: float,
        total_btc: float,
        monthly_target: float,
        locale: str = None,
    ) -> dict:
        """
        Return a formatted savings summary dict.
        """
        loc = locale or self._default_locale
        return {
            "total_saved_display":  NumberFormatter.format_currency(total_usd, "USD", loc),
            "total_btc_display":    NumberFormatter.format_bitcoin(total_btc, loc),
            "monthly_target_display": NumberFormatter.format_currency(monthly_target, "USD", loc),
            "labels": {
                "total_saved":  self._t.translate("savings.total_saved", locale=loc),
                "total_btc":    self._t.translate("savings.total_btc", locale=loc),
                "monthly_target": self._t.translate("savings.monthly_target", locale=loc),
            },
        }

    def format_deposit_confirmation(
        self,
        amount_usd: float,
        btc_amount: float,
        total_usd: float,
        locale: str = None,
    ) -> dict:
        """Return a formatted deposit confirmation message."""
        loc = locale or self._default_locale
        amount_str = NumberFormatter.format_currency(amount_usd, "USD", loc)
        total_str  = NumberFormatter.format_currency(total_usd, "USD", loc)

        return {
            "message": self._t.translate("savings.deposit.recorded", locale=loc, amount=amount_str),
            "amount":  amount_str,
            "btc":     NumberFormatter.format_bitcoin(btc_amount),
            "total":   total_str,
            "notification": self.format_notification_full("deposit", locale=loc, amount=amount_str, total=total_str),
        }
