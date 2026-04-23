"""Phone + OTP authentication for Salvadoran users.

Flow:
1. User enters phone number (+503 XXXX-XXXX)
2. Server generates 6-digit OTP, stores it, sends via SMS
3. User enters OTP
4. Server verifies OTP, creates session with a deterministic user ID
"""

import hashlib
import re
import secrets
import time
import threading

from .sessions import create_session
from ..database import get_conn, _is_postgres
from ..i18n import t

_otps: dict[str, dict] = {}  # phone -> {code, expires_at, attempts}
_lock = threading.Lock()

OTP_TTL = 300  # 5 minutes
MAX_ATTEMPTS = 5
RATE_LIMIT_WINDOW = 60
_rate_limits: dict[str, list[float]] = {}

# Salvadoran phone: 6xxx-xxxx or 7xxx-xxxx (mobile) or 2xxx-xxxx (landline)
_SV_PHONE_RE = re.compile(r"^\+?503?\s*([267]\d{3})\s*-?\s*(\d{4})$")


def _normalize_phone(raw: str) -> str | None:
    """Normalize to +503XXXXXXXX format. Returns None if invalid."""
    cleaned = raw.strip().replace(" ", "").replace("-", "")
    # If they just typed 8 digits starting with 2/6/7
    if re.match(r"^[267]\d{7}$", cleaned):
        return f"+503{cleaned}"
    # If they typed with country code
    if re.match(r"^\+?503[267]\d{7}$", cleaned):
        if not cleaned.startswith("+"):
            cleaned = f"+{cleaned}"
        return cleaned
    return None


def _phone_to_pubkey(phone: str) -> str:
    """Derive a deterministic 64-char hex identifier from a phone number.

    This lets phone-auth users fit into the existing pubkey-based system.
    """
    return hashlib.sha256(f"magma:phone:{phone}".encode()).hexdigest()


def _send_sms(phone: str, code: str) -> bool:
    """Send SMS with OTP code.

    Currently logs to console. Replace with Twilio/etc. in production.
    """
    print(f"[SMS] Code {code} -> {phone}", flush=True)
    return True


def handle_phone_send(body: dict) -> tuple[dict, int]:
    """POST /auth/phone — Send OTP to phone number."""
    raw_phone = body.get("phone", "")
    phone = _normalize_phone(raw_phone)
    if not phone:
        return {"detail": t("auth.phone.invalid")}, 400

    # Rate limit
    now = time.time()
    if phone in _rate_limits:
        _rate_limits[phone] = [ts for ts in _rate_limits[phone] if now - ts < RATE_LIMIT_WINDOW]
        if len(_rate_limits[phone]) >= 3:
            return {"detail": t("error.rate_limited")}, 429
    else:
        _rate_limits[phone] = []
    _rate_limits[phone].append(now)

    code = f"{secrets.randbelow(900000) + 100000}"

    with _lock:
        _otps[phone] = {
            "code": code,
            "expires_at": now + OTP_TTL,
            "attempts": 0,
        }

    _send_sms(phone, code)

    from ..config import settings

    response = {
        "status": "sent",
        "phone": phone[:7] + "****",
        "expires_in": OTP_TTL,
    }
    if settings.DEV_MODE:
        response["dev_code"] = code
    return response, 200


def handle_phone_verify(body: dict) -> tuple[dict, int]:
    """POST /auth/phone/verify — Verify OTP and create session."""
    raw_phone = body.get("phone", "")
    code = body.get("code", "").strip()
    phone = _normalize_phone(raw_phone)

    if not phone:
        return {"detail": t("auth.phone.invalid")}, 400

    if not code or len(code) != 6:
        return {"detail": t("auth.phone.code.invalid")}, 400

    with _lock:
        otp_data = _otps.get(phone)

    if otp_data is None:
        return {"detail": t("auth.phone.code.expired")}, 401

    if time.time() > otp_data["expires_at"]:
        with _lock:
            _otps.pop(phone, None)
        return {"detail": t("auth.phone.code.expired")}, 401

    otp_data["attempts"] += 1
    if otp_data["attempts"] > MAX_ATTEMPTS:
        with _lock:
            _otps.pop(phone, None)
        return {"detail": t("error.rate_limited")}, 429

    if otp_data["code"] != code:
        return {"detail": t("auth.phone.code.invalid")}, 401

    # OTP valid — clean up and create session
    with _lock:
        _otps.pop(phone, None)

    pubkey = _phone_to_pubkey(phone)
    token = create_session(pubkey)

    # Upsert user in database
    try:
        conn = get_conn()
        now = int(time.time())
        if _is_postgres():
            conn.execute(
                "INSERT INTO users (pubkey, auth_method, created_at) VALUES (%s, 'phone', %s) ON CONFLICT (pubkey) DO NOTHING",
                (pubkey, now),
            )
        else:
            conn.execute(
                "INSERT OR IGNORE INTO users (pubkey, auth_method, created_at) VALUES (?, 'phone', ?)",
                (pubkey, now),
            )
        conn.commit()
    except Exception:
        pass

    return {"status": "ok", "token": token, "pubkey": pubkey}, 200
