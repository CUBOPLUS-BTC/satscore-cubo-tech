"""Bitcoin unit conversion and formatting utilities.

All functions are pure; no DB access or network calls.
Covers satoshis, BTC, USD, millisatoshis, and human-readable
formatting with locale-style separators.
"""

import math
import re

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SATOSHIS_PER_BTC: int = 100_000_000
MSATS_PER_SAT: int = 1000
MSATS_PER_BTC: int = SATOSHIS_PER_BTC * MSATS_PER_SAT


# ---------------------------------------------------------------------------
# Basic conversions
# ---------------------------------------------------------------------------


def sats_to_btc(sats: int) -> float:
    """Convert an integer satoshi amount to BTC.

    >>> sats_to_btc(100_000_000)
    1.0
    >>> sats_to_btc(1)
    1e-08
    """
    return sats / SATOSHIS_PER_BTC


def btc_to_sats(btc: float) -> int:
    """Convert a BTC float to satoshis (rounded to nearest integer).

    >>> btc_to_sats(1.0)
    100000000
    >>> btc_to_sats(0.00000001)
    1
    """
    return int(round(btc * SATOSHIS_PER_BTC))


def sats_to_usd(sats: int, btc_price: float) -> float:
    """Convert satoshis to USD given a BTC/USD price.

    Parameters
    ----------
    sats:
        Amount in satoshis.
    btc_price:
        Current BTC price in USD.

    Returns
    -------
    float  — USD value, rounded to 2 decimal places.
    """
    if btc_price <= 0:
        return 0.0
    return round(sats_to_btc(sats) * btc_price, 2)


def usd_to_sats(usd: float, btc_price: float) -> int:
    """Convert a USD amount to satoshis given a BTC/USD price.

    Parameters
    ----------
    usd:
        Amount in USD.
    btc_price:
        Current BTC price in USD.

    Returns
    -------
    int  — Satoshi equivalent (floored).
    """
    if btc_price <= 0:
        return 0
    return btc_to_sats(usd / btc_price)


def msats_to_sats(msats: int) -> float:
    """Convert millisatoshis to satoshis."""
    return msats / MSATS_PER_SAT


def sats_to_msats(sats: int) -> int:
    """Convert satoshis to millisatoshis."""
    return sats * MSATS_PER_SAT


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def format_sats(sats: int) -> str:
    """Format a satoshi amount with thousands separators.

    >>> format_sats(1_234_567)
    '1,234,567 sats'
    >>> format_sats(1_000)
    '1,000 sats'
    """
    return f"{int(sats):,} sats"


def format_btc(btc: float, precision: int = 8) -> str:
    """Format a BTC amount with the specified decimal precision.

    Parameters
    ----------
    btc:
        BTC amount.
    precision:
        Number of decimal places (default 8, range 0-8).

    >>> format_btc(1.5)
    '1.50000000 BTC'
    >>> format_btc(0.001, precision=3)
    '0.001 BTC'
    """
    precision = max(0, min(8, precision))
    return f"{btc:.{precision}f} BTC"


def format_usd(usd: float) -> str:
    """Format a USD value with dollar sign and two decimal places.

    >>> format_usd(1234.5)
    '$1,234.50'
    >>> format_usd(-99.9)
    '-$99.90'
    """
    if usd < 0:
        return f"-${abs(usd):,.2f}"
    return f"${usd:,.2f}"


def format_msats(msats: int) -> str:
    """Format millisatoshis with a human-readable suffix.

    >>> format_msats(1000)
    '1,000 msats (1 sat)'
    """
    sats = msats // MSATS_PER_SAT
    remainder = msats % MSATS_PER_SAT
    sat_str = f"{sats:,} sat" if sats == 1 else f"{sats:,} sats"
    if remainder:
        return f"{msats:,} msats ({sat_str} + {remainder} msat remainder)"
    return f"{msats:,} msats ({sat_str})"


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------

_AMOUNT_PATTERN = re.compile(
    r"^\s*([+-]?\d+(?:[.,]\d+)*)\s*(btc|sat|sats|satoshi|satoshis|usd|\$|msat|msats)?\s*$",
    re.IGNORECASE,
)


def parse_amount(amount_str: str) -> dict:
    """Parse a human-entered amount string into a structured representation.

    Accepted formats:
        "0.01 BTC", "100000 sats", "100000 sat", "$50.00",
        "50 USD", "1500 msats"

    Parameters
    ----------
    amount_str:
        Raw input string.

    Returns
    -------
    dict with keys:
        raw (str), numeric (float), unit (str),
        sats (int | None), btc (float | None),
        usd (float | None), valid (bool), detail (str)
    """
    base = {
        "raw": amount_str,
        "numeric": 0.0,
        "unit": "unknown",
        "sats": None,
        "btc": None,
        "usd": None,
        "valid": False,
        "detail": "Unrecognised format",
    }

    if not amount_str or not isinstance(amount_str, str):
        return base

    # Normalise thousands separator (commas) before float parsing
    cleaned = amount_str.strip().replace(",", "")
    m = _AMOUNT_PATTERN.match(cleaned)
    if not m:
        return base

    try:
        numeric = float(m.group(1))
    except ValueError:
        return base

    raw_unit = (m.group(2) or "").lower().strip("$")
    base["numeric"] = numeric

    if raw_unit in ("btc", "") and "." in cleaned.split(raw_unit or " ")[0]:
        # Ambiguous: treat bare decimal values > 21M as sats, else BTC
        unit = "btc" if numeric <= 21_000_000 else "sats"
    elif raw_unit in ("sat", "sats", "satoshi", "satoshis"):
        unit = "sats"
    elif raw_unit in ("msat", "msats"):
        unit = "msats"
    elif raw_unit in ("usd", "$"):
        unit = "usd"
    elif raw_unit == "btc":
        unit = "btc"
    else:
        # bare integer — heuristic
        unit = "sats" if numeric == int(numeric) and numeric > 0.21 else "btc"

    base["unit"] = unit

    if unit == "btc":
        base["btc"] = numeric
        base["sats"] = btc_to_sats(numeric)
        base["valid"] = True
        base["detail"] = f"Parsed as {format_btc(numeric)}"
    elif unit == "sats":
        base["sats"] = int(numeric)
        base["btc"] = sats_to_btc(int(numeric))
        base["valid"] = True
        base["detail"] = f"Parsed as {format_sats(int(numeric))}"
    elif unit == "msats":
        base["sats"] = int(numeric) // MSATS_PER_SAT
        base["btc"] = sats_to_btc(base["sats"])
        base["valid"] = True
        base["detail"] = f"Parsed as {format_msats(int(numeric))}"
    elif unit == "usd":
        base["usd"] = numeric
        base["valid"] = True
        base["detail"] = f"Parsed as {format_usd(numeric)} (BTC price required for sats conversion)"

    return base


# ---------------------------------------------------------------------------
# Purchasing power
# ---------------------------------------------------------------------------

# Representative item prices in USD (updated periodically)
_DEFAULT_ITEMS = {
    "cup_of_coffee": 5.00,
    "big_mac": 6.50,
    "streaming_subscription": 15.99,
    "monthly_rent_us_avg": 1_500.00,
    "new_car_us_avg": 48_000.00,
    "median_us_house": 420_000.00,
    "gold_1oz": 2_300.00,
    "sp500_share_avg": 550.00,
}


def calculate_purchasing_power(
    sats: int,
    btc_price: float,
    items: dict | None = None,
) -> dict:
    """Calculate what the sats holding is worth in everyday terms.

    Parameters
    ----------
    sats:
        Satoshi amount to evaluate.
    btc_price:
        Current BTC/USD price.
    items:
        Optional dict of {item_name: price_usd}.  Defaults to a set
        of common reference items.

    Returns
    -------
    dict with keys:
        sats (int), btc (float), usd_value (float),
        purchasing_power (list of {item, price_usd, quantity, unit})
    """
    if items is None:
        items = _DEFAULT_ITEMS

    usd = sats_to_usd(sats, btc_price)
    btc = sats_to_btc(sats)

    power = []
    for item_name, price_usd in items.items():
        if price_usd > 0:
            quantity = usd / price_usd
            label = item_name.replace("_", " ").title()
            unit = "units"
            if quantity >= 1:
                unit = "full units"
            power.append({
                "item": label,
                "price_usd": price_usd,
                "quantity": round(quantity, 4),
                "unit": unit,
                "can_afford": quantity >= 1.0,
            })

    power.sort(key=lambda x: x["price_usd"])

    return {
        "sats": sats,
        "btc": round(btc, 8),
        "usd_value": usd,
        "purchasing_power": power,
    }


# ---------------------------------------------------------------------------
# Conversion summary helper
# ---------------------------------------------------------------------------


def conversion_summary(sats: int, btc_price: float) -> dict:
    """Return a complete conversion summary for a given satoshi amount.

    Useful for API responses that need all unit representations at once.

    Returns
    -------
    dict with keys:
        sats, msats, btc, usd, formatted_sats, formatted_btc, formatted_usd
    """
    btc = sats_to_btc(sats)
    usd = sats_to_usd(sats, btc_price)
    return {
        "sats": sats,
        "msats": sats_to_msats(sats),
        "btc": btc,
        "usd": usd,
        "formatted_sats": format_sats(sats),
        "formatted_btc": format_btc(btc),
        "formatted_usd": format_usd(usd),
    }
