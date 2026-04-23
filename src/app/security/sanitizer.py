"""
Input sanitization and validation for Magma Bitcoin app.
Provides protection against XSS, SQL injection, path traversal, and command injection.
All methods are pure Python stdlib — no third-party dependencies.
"""

import re
import unicodedata
import urllib.parse
import html
import json
import os
from typing import Any


# ---------------------------------------------------------------------------
# Pre-compiled regular expressions
# ---------------------------------------------------------------------------

_SQL_INJECTION_PATTERNS = re.compile(
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|"
    r"HAVING|TRUNCATE|CAST|CONVERT|DECLARE|NCHAR|CHAR|VARCHAR|CURSOR|FETCH|"
    r"KILL|OPEN|SYSOBJECTS|SYSCOLUMNS|INFORMATION_SCHEMA)\b"
    r"|--|;|/\*|\*/|xp_|0x[0-9a-fA-F]+|\bOR\b\s+\d+\s*=\s*\d+"
    r"|\bAND\b\s+\d+\s*=\s*\d+|'\s*(OR|AND)\s*')",
    re.IGNORECASE,
)

_XSS_PATTERNS = re.compile(
    r"(<script[\s\S]*?>[\s\S]*?</script>|<script[^>]*>|</script>"
    r"|javascript\s*:|vbscript\s*:|data\s*:|on\w+\s*=|<\s*iframe"
    r"|<\s*object|<\s*embed|<\s*applet|<\s*meta|<\s*link"
    r"|expression\s*\(|url\s*\(|@import|\beval\s*\(|\bexec\s*\()",
    re.IGNORECASE,
)

_COMMAND_INJECTION_PATTERNS = re.compile(
    r"(;|\||&&|\$\(|`|>\s*/|<\s*/|\bsudo\b|\brm\b|\bchmod\b|\bchown\b"
    r"|\bwget\b|\bcurl\b|\bnc\b|\bnetcat\b|\bpython\b|\bperl\b|\bruby\b"
    r"|\bphp\b|\bbash\b|\bsh\b|\bpowershell\b|\bcmd\b"
    r"|/etc/passwd|/etc/shadow|/bin/sh|/bin/bash)",
    re.IGNORECASE,
)

_PATH_TRAVERSAL_PATTERNS = re.compile(
    r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e/|\.%2e/|%2e\./|%252e%252e%252f"
    r"|\.{2,}[/\\]|[/\\]\.{2,})",
    re.IGNORECASE,
)

_VALID_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)

_VALID_BITCOIN_ADDRESS = re.compile(
    r"^(bc1[ac-hj-np-z02-9]{25,90}|[13][a-km-zA-HJ-NP-Z1-9]{25,34}"
    r"|tb1[ac-hj-np-z02-9]{25,90}|[mn2][a-km-zA-HJ-NP-Z1-9]{25,34})$"
)

_VALID_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")

_VALID_LIGHTNING_INVOICE = re.compile(
    r"^(lnbc|lntb|lnbcrt|lnsb)[0-9]*(u|m|n|p)?1[a-z0-9]+$",
    re.IGNORECASE,
)

_VALID_ISO_DATE = re.compile(
    r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$"
)

_VALID_CURRENCY_CODE = re.compile(r"^[A-Z]{3}$")

_SAFE_SQL_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$")

_DANGEROUS_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f]")

_UNICODE_HOMOGRAPH_RANGES = [
    (0x0400, 0x04FF),   # Cyrillic
    (0x0370, 0x03FF),   # Greek
    (0x0250, 0x02AF),   # IPA Extensions
    (0x1D00, 0x1D7F),   # Phonetic Extensions
    (0x2070, 0x209F),   # Superscripts and Subscripts
    (0xFF00, 0xFFEF),   # Halfwidth and Fullwidth Forms
]


# ---------------------------------------------------------------------------
# Sanitizer
# ---------------------------------------------------------------------------

class Sanitizer:
    """
    Central input sanitization class.
    All methods are safe to call with None or unexpected types — they will
    return a safe empty value rather than raising.
    """

    # ------------------------------------------------------------------
    # Basic string sanitization
    # ------------------------------------------------------------------

    @staticmethod
    def sanitize_string(s: Any, max_length: int = 256) -> str:
        """
        Strip control characters, normalize whitespace, and truncate.
        Returns empty string for non-string input.
        """
        if not isinstance(s, str):
            try:
                s = str(s)
            except Exception:
                return ""

        # Remove null bytes and other dangerous control characters
        s = _DANGEROUS_CHARS.sub("", s)

        # Normalize line endings
        s = s.replace("\r\n", "\n").replace("\r", "\n")

        # Strip leading/trailing whitespace
        s = s.strip()

        # Truncate to max_length
        if len(s) > max_length:
            s = s[:max_length]

        return s

    @staticmethod
    def sanitize_html(s: Any) -> str:
        """
        Escape all HTML entities to prevent XSS.
        Converts <, >, &, ", ' to their HTML entity equivalents.
        """
        if not isinstance(s, str):
            try:
                s = str(s)
            except Exception:
                return ""

        return html.escape(s, quote=True)

    @staticmethod
    def sanitize_url(url: Any) -> str:
        """
        Validate and sanitize a URL.
        Only allows http and https schemes.
        Returns empty string for invalid or dangerous URLs.
        """
        if not isinstance(url, str):
            return ""

        url = url.strip()
        if not url:
            return ""

        try:
            parsed = urllib.parse.urlparse(url)
        except Exception:
            return ""

        # Only allow safe schemes
        if parsed.scheme not in ("http", "https"):
            return ""

        # Reject javascript: and data: URIs that might have slipped through
        if re.match(r"^(javascript|vbscript|data):", url, re.IGNORECASE):
            return ""

        # Reject URLs with credentials embedded
        if parsed.username or parsed.password:
            return ""

        # Re-encode the URL to normalize it
        try:
            sanitized = urllib.parse.urlunparse((
                parsed.scheme,
                parsed.netloc,
                urllib.parse.quote(parsed.path, safe="/-._~:@!$&'()*+,;="),
                parsed.params,
                urllib.parse.quote(parsed.query, safe="=&+%"),
                "",
            ))
        except Exception:
            return ""

        return sanitized

    @staticmethod
    def sanitize_email(email: Any) -> str:
        """
        Validate and normalize an email address.
        Returns empty string for invalid emails.
        """
        if not isinstance(email, str):
            return ""

        email = email.strip().lower()

        if len(email) > 254:
            return ""

        if not _VALID_EMAIL_PATTERN.match(email):
            return ""

        # Extra: ensure local part <= 64 chars
        local, _, domain = email.partition("@")
        if len(local) > 64:
            return ""

        # Reject consecutive dots
        if ".." in email:
            return ""

        return email

    @staticmethod
    def sanitize_json(data: Any, schema: dict) -> dict:
        """
        Validate a dict against a simple schema and return only known fields.

        Schema format::

            {
                "field_name": {
                    "type": "str" | "int" | "float" | "bool" | "list" | "dict",
                    "required": True | False,
                    "max_length": int,       # for strings
                    "min": number,           # for numbers
                    "max": number,           # for numbers
                    "choices": [...]         # allowed values
                }
            }
        """
        if not isinstance(data, dict):
            return {}

        result: dict = {}
        errors: list = []

        for field, spec in schema.items():
            value = data.get(field)
            required = spec.get("required", False)
            expected_type = spec.get("type", "str")

            if value is None:
                if required:
                    errors.append(f"Field '{field}' is required")
                continue

            # Type coercion / validation
            try:
                if expected_type == "str":
                    value = Sanitizer.sanitize_string(
                        str(value), spec.get("max_length", 256)
                    )
                elif expected_type == "int":
                    value = int(value)
                elif expected_type == "float":
                    value = float(value)
                elif expected_type == "bool":
                    if isinstance(value, bool):
                        pass
                    elif isinstance(value, int):
                        value = bool(value)
                    elif isinstance(value, str):
                        value = value.lower() in ("true", "1", "yes")
                    else:
                        value = bool(value)
                elif expected_type == "list":
                    if not isinstance(value, list):
                        continue
                elif expected_type == "dict":
                    if not isinstance(value, dict):
                        continue
            except (ValueError, TypeError):
                errors.append(f"Field '{field}' has invalid type (expected {expected_type})")
                continue

            # Range validation for numbers
            if expected_type in ("int", "float"):
                if "min" in spec and value < spec["min"]:
                    errors.append(
                        f"Field '{field}' must be >= {spec['min']}, got {value}"
                    )
                    continue
                if "max" in spec and value > spec["max"]:
                    errors.append(
                        f"Field '{field}' must be <= {spec['max']}, got {value}"
                    )
                    continue

            # Choices validation
            if "choices" in spec and value not in spec["choices"]:
                errors.append(
                    f"Field '{field}' must be one of {spec['choices']}, got {value!r}"
                )
                continue

            result[field] = value

        # Attach validation errors to result (non-fatal — caller decides)
        if errors:
            result["_validation_errors"] = errors

        return result

    @staticmethod
    def sanitize_path(path: Any) -> str:
        """
        Sanitize a file path to prevent directory traversal attacks.
        Normalizes separators, removes traversal sequences.
        Returns empty string if the path is deemed unsafe.
        """
        if not isinstance(path, str):
            return ""

        path = path.strip()

        # URL-decode to catch encoded traversal
        try:
            path = urllib.parse.unquote(path)
        except Exception:
            return ""

        # Reject immediately if traversal pattern is detected
        if _PATH_TRAVERSAL_PATTERNS.search(path):
            return ""

        # Normalize OS separators and collapse multiple slashes
        path = path.replace("\\", "/")
        path = re.sub(r"/+", "/", path)

        # Remove any remaining dot-dot segments after normalization
        parts = path.split("/")
        clean: list = []
        for part in parts:
            if part in (".", ".."):
                continue
            clean.append(part)

        result = "/".join(clean).strip("/")

        # Final rejection: absolute paths are not allowed
        if result.startswith("/"):
            return ""

        return result

    @staticmethod
    def sanitize_sql_identifier(s: Any) -> str:
        """
        Ensure a string is safe to use as a SQL table or column identifier.
        Returns empty string if it doesn't match the safe pattern.
        """
        if not isinstance(s, str):
            return ""

        s = s.strip()
        if _SAFE_SQL_IDENTIFIER.match(s):
            return s

        return ""

    @staticmethod
    def detect_injection(s: Any) -> dict:
        """
        Analyze a string for multiple injection attack types.

        Returns::

            {
                "safe": bool,
                "sql_injection": bool,
                "xss": bool,
                "command_injection": bool,
                "path_traversal": bool,
                "risk_score": int   # 0-100
            }
        """
        if not isinstance(s, str):
            return {"safe": True, "sql_injection": False, "xss": False,
                    "command_injection": False, "path_traversal": False, "risk_score": 0}

        sql = bool(_SQL_INJECTION_PATTERNS.search(s))
        xss = bool(_XSS_PATTERNS.search(s))
        cmd = bool(_COMMAND_INJECTION_PATTERNS.search(s))
        path = bool(_PATH_TRAVERSAL_PATTERNS.search(s))

        risk = sum([sql * 40, xss * 35, cmd * 45, path * 30])
        risk = min(risk, 100)

        return {
            "safe": not any([sql, xss, cmd, path]),
            "sql_injection": sql,
            "xss": xss,
            "command_injection": cmd,
            "path_traversal": path,
            "risk_score": risk,
        }

    @staticmethod
    def detect_xss(s: Any) -> bool:
        """Return True if the string contains XSS patterns."""
        if not isinstance(s, str):
            return False
        return bool(_XSS_PATTERNS.search(s))

    @staticmethod
    def detect_sql_injection(s: Any) -> bool:
        """Return True if the string contains SQL injection patterns."""
        if not isinstance(s, str):
            return False
        return bool(_SQL_INJECTION_PATTERNS.search(s))

    @staticmethod
    def detect_command_injection(s: Any) -> bool:
        """Return True if the string contains command injection patterns."""
        if not isinstance(s, str):
            return False
        return bool(_COMMAND_INJECTION_PATTERNS.search(s))

    @staticmethod
    def escape_for_shell(s: Any) -> str:
        """
        Escape a string so it is safe to use inside a shell single-quoted string.
        Replaces every single quote with '\\'' to break and re-open the quoting.
        Returns the string wrapped in single quotes.
        NOTE: Prefer subprocess with list args over shell=True whenever possible.
        """
        if not isinstance(s, str):
            s = str(s)

        # Remove null bytes
        s = s.replace("\x00", "")

        # Escape single quotes
        s = s.replace("'", "'\\''")

        return f"'{s}'"

    @staticmethod
    def normalize_unicode(s: Any) -> str:
        """
        Normalize Unicode to NFC form and optionally flag homograph characters.
        This helps prevent Unicode-based homograph attacks where visually similar
        characters from different scripts are substituted for ASCII characters.
        """
        if not isinstance(s, str):
            return ""

        # Normalize to NFC (Canonical Decomposition, followed by Canonical Composition)
        normalized = unicodedata.normalize("NFC", s)

        # Replace common confusables in the Cyrillic block that look like Latin
        confusables = {
            "\u0430": "a",  # Cyrillic а → Latin a
            "\u0435": "e",  # Cyrillic е → Latin e
            "\u043e": "o",  # Cyrillic о → Latin o
            "\u0440": "p",  # Cyrillic р → Latin p
            "\u0441": "c",  # Cyrillic с → Latin c
            "\u0445": "x",  # Cyrillic х → Latin x
            "\u0443": "y",  # Cyrillic у → Latin y
            "\u0456": "i",  # Cyrillic і → Latin i
            "\u0454": "e",  # Cyrillic є → Latin e
            "\u0460": "O",  # Omega
            "\u03bf": "o",  # Greek omicron → Latin o
            "\u03b1": "a",  # Greek alpha → Latin a
        }

        result = []
        for ch in normalized:
            result.append(confusables.get(ch, ch))

        return "".join(result)


# ---------------------------------------------------------------------------
# InputValidator
# ---------------------------------------------------------------------------

class InputValidator:
    """
    Domain-specific validation for Bitcoin, Nostr, and financial inputs.
    All methods return bool and never raise exceptions.
    """

    @staticmethod
    def validate_bitcoin_address(addr: Any) -> bool:
        """
        Validate a Bitcoin address (mainnet, testnet, bech32, legacy).
        Supports P2PKH (1...), P2SH (3...), native SegWit (bc1...) and
        testnet equivalents.
        """
        if not isinstance(addr, str):
            return False

        addr = addr.strip()
        if not addr:
            return False

        return bool(_VALID_BITCOIN_ADDRESS.match(addr))

    @staticmethod
    def validate_nostr_pubkey(key: Any) -> bool:
        """
        Validate a Nostr public key (64-character lowercase hex string).
        """
        if not isinstance(key, str):
            return False

        key = key.strip().lower()
        return bool(_VALID_HEX64.match(key))

    @staticmethod
    def validate_lightning_invoice(invoice: Any) -> bool:
        """
        Validate a BOLT-11 Lightning Network invoice.
        Checks the human-readable part prefix (lnbc, lntb, etc.) and
        confirms the invoice uses only valid characters.
        """
        if not isinstance(invoice, str):
            return False

        invoice = invoice.strip().lower()

        if len(invoice) < 20 or len(invoice) > 4096:
            return False

        return bool(_VALID_LIGHTNING_INVOICE.match(invoice))

    @staticmethod
    def validate_amount(amount: Any, min_val: Any = 0, max_val: Any = 10_000_000) -> bool:
        """
        Validate a numeric amount within a range.
        Accepts int or float. min_val defaults to 0, max_val to 10M.
        """
        try:
            amount = float(amount)
            min_val = float(min_val)
            max_val = float(max_val)
        except (TypeError, ValueError):
            return False

        if amount != amount:  # NaN check
            return False

        return min_val <= amount <= max_val

    @staticmethod
    def validate_iso_date(date_str: Any) -> bool:
        """
        Validate an ISO 8601 date string (YYYY-MM-DD).
        Also performs calendar validation (e.g., no Feb 30).
        """
        if not isinstance(date_str, str):
            return False

        date_str = date_str.strip()
        if not _VALID_ISO_DATE.match(date_str):
            return False

        try:
            year, month, day = [int(p) for p in date_str.split("-")]
        except ValueError:
            return False

        # Calendar validation
        days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        # Leap year
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            days_in_month[2] = 29

        if month < 1 or month > 12:
            return False
        if day < 1 or day > days_in_month[month]:
            return False

        return True

    @staticmethod
    def validate_currency_code(code: Any) -> bool:
        """
        Validate an ISO 4217 three-letter currency code.
        Checks format only (does not verify against full SWIFT list).
        """
        if not isinstance(code, str):
            return False

        return bool(_VALID_CURRENCY_CODE.match(code.strip()))

    @staticmethod
    def validate_integer_string(s: Any, min_val: int = 0, max_val: int = 2**63) -> bool:
        """Validate that a string represents a valid integer within range."""
        try:
            val = int(str(s).strip())
            return min_val <= val <= max_val
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_hex_string(s: Any, expected_length: int = None) -> bool:
        """Validate a hexadecimal string, optionally with an exact length."""
        if not isinstance(s, str):
            return False

        s = s.strip().lower()
        if not re.match(r"^[0-9a-f]+$", s):
            return False

        if expected_length is not None and len(s) != expected_length:
            return False

        return True

    @staticmethod
    def validate_base64(s: Any) -> bool:
        """Validate a base64-encoded string (standard or URL-safe alphabet)."""
        if not isinstance(s, str):
            return False
        import base64 as b64_module
        try:
            # Pad if necessary
            padded = s + "=" * (4 - len(s) % 4) if len(s) % 4 else s
            b64_module.b64decode(padded, validate=True)
            return True
        except Exception:
            return False

    @staticmethod
    def validate_ip_address(ip: Any) -> bool:
        """Validate an IPv4 or IPv6 address string."""
        import ipaddress
        if not isinstance(ip, str):
            return False
        try:
            ipaddress.ip_address(ip.strip())
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_port(port: Any) -> bool:
        """Validate a network port number (1-65535)."""
        try:
            p = int(port)
            return 1 <= p <= 65535
        except (TypeError, ValueError):
            return False

    @staticmethod
    def validate_pubkey_list(keys: Any) -> bool:
        """Validate that input is a non-empty list of valid Nostr pubkeys."""
        if not isinstance(keys, list) or not keys:
            return False
        return all(InputValidator.validate_nostr_pubkey(k) for k in keys)

    @staticmethod
    def validate_json_string(s: Any) -> bool:
        """Validate that a string contains valid JSON."""
        if not isinstance(s, str):
            return False
        try:
            json.loads(s)
            return True
        except (json.JSONDecodeError, ValueError):
            return False

    @staticmethod
    def sanitize_and_validate_all(data: dict, schema: dict) -> tuple[dict, list]:
        """
        Combined sanitization and validation pass.
        Returns (cleaned_data, errors_list).
        Errors list is empty on full success.
        """
        sanitizer = Sanitizer()
        cleaned = sanitizer.sanitize_json(data, schema)
        errors = cleaned.pop("_validation_errors", [])

        # Additional injection checks on string fields
        injection_errors = []
        for key, value in cleaned.items():
            if isinstance(value, str):
                result = sanitizer.detect_injection(value)
                if not result["safe"]:
                    injection_errors.append(
                        f"Field '{key}' contains potentially malicious content "
                        f"(risk_score={result['risk_score']})"
                    )

        all_errors = errors + injection_errors
        return cleaned, all_errors
