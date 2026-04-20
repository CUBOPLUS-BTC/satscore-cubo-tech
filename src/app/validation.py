"""Input validation helpers used by routes and business logic."""

import math
import re

_HEX_PUBKEY_RE = re.compile(r"^[a-fA-F0-9]{64}$")


def validate_pubkey(s: str) -> bool:
    """Return True if s is a 64-char hex pubkey."""
    return isinstance(s, str) and bool(_HEX_PUBKEY_RE.match(s))


def validate_amount(
    n: float, min_val: float = 0, max_val: float = 1_000_000
) -> bool:
    """Return True if n is a finite number within [min_val, max_val].

    Rejects booleans, NaN and infinities. Booleans are rejected to avoid
    ``True`` being silently accepted as ``1``.
    """
    if isinstance(n, bool) or not isinstance(n, (int, float)):
        return False
    if not math.isfinite(n):
        return False
    return min_val <= n <= max_val


def validate_years(n: int, min_val: int = 1, max_val: int = 50) -> bool:
    """Return True if n is an integer within [min_val, max_val]."""
    if isinstance(n, bool) or not isinstance(n, int):
        return False
    return min_val <= n <= max_val


def validate_string(s: str, max_len: int = 256) -> bool:
    """Return True if s is non-empty and no longer than max_len."""
    return isinstance(s, str) and bool(s) and len(s) <= max_len
