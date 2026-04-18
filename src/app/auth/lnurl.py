"""LNURL-auth implementation (LUD-04).

Flow:
1. Server generates k1 challenge, encodes callback URL as LNURL bech32
2. Frontend renders LNURL as QR code
3. User's wallet scans QR, derives linking key, signs k1, calls callback
4. Server verifies secp256k1 signature, creates session token
5. Frontend polls status endpoint until authenticated
"""

import secrets
import time
import threading
from .bech32 import lnurl_encode
from .sessions import create_session
from ..database import get_conn, _is_postgres

_lnurl_sessions: dict[str, dict] = {}  # k1 -> session data
_lock = threading.Lock()

CHALLENGE_TTL = 300  # 5 minutes


def create_lnurl_challenge() -> dict:
    """Generate a new LNURL-auth challenge.

    Returns dict with k1, lnurl, and expires_at.
    Uses PUBLIC_URL from config for the callback URL.
    """
    from ..config import settings

    k1 = secrets.token_hex(32)
    expires_at = time.time() + CHALLENGE_TTL

    callback_url = f"{settings.PUBLIC_URL}/auth/lnurl-callback?tag=login&k1={k1}"
    lnurl = lnurl_encode(callback_url)

    with _lock:
        _lnurl_sessions[k1] = {
            "status": "pending",
            "expires_at": expires_at,
            "pubkey": None,
            "token": None,
        }

    return {
        "k1": k1,
        "lnurl": lnurl,
        "qr_data": lnurl,
        "expires_at": int(expires_at),
    }


def verify_lnurl_callback(k1: str, sig: str, key: str) -> bool:
    """Verify the LNURL-auth callback from the user's wallet.

    Args:
        k1: The challenge hex string
        sig: DER-encoded signature hex
        key: Compressed public key hex (33 bytes / 66 chars)

    Returns True if signature is valid and session is created.
    """
    with _lock:
        session = _lnurl_sessions.get(k1)
        if session is None:
            return False
        if session["status"] != "pending":
            return False
        if time.time() > session["expires_at"]:
            del _lnurl_sessions[k1]
            return False

    # Verify secp256k1 signature
    try:
        from coincurve import PublicKey

        pubkey = PublicKey(bytes.fromhex(key))
        msg = bytes.fromhex(k1)
        sig_bytes = bytes.fromhex(sig)

        is_valid = pubkey.verify(sig_bytes, msg, hasher=None)
    except Exception:
        return False

    if not is_valid:
        return False

    # Create session token
    token = create_session(key)

    # Upsert user in database
    try:
        conn = get_conn()
        now = int(time.time())
        if _is_postgres():
            conn.execute(
                "INSERT INTO users (pubkey, auth_method, created_at) VALUES (%s, 'lnurl', %s) ON CONFLICT (pubkey) DO NOTHING",
                (key, now),
            )
        else:
            conn.execute(
                "INSERT OR IGNORE INTO users (pubkey, auth_method, created_at) VALUES (?, 'lnurl', ?)",
                (key, now),
            )
        conn.commit()
    except Exception:
        pass

    with _lock:
        _lnurl_sessions[k1] = {
            "status": "ok",
            "expires_at": session["expires_at"],
            "pubkey": key,
            "token": token,
        }

    return True


def get_lnurl_status(k1: str) -> dict:
    """Check the status of an LNURL-auth session.

    Returns dict with status, and optionally token + pubkey if authenticated.
    """
    with _lock:
        session = _lnurl_sessions.get(k1)

    if session is None:
        return {"status": "error", "reason": "Unknown session"}

    if time.time() > session["expires_at"]:
        with _lock:
            _lnurl_sessions.pop(k1, None)
        return {"status": "expired"}

    if session["status"] == "ok":
        # Clean up after delivery
        result = {
            "status": "ok",
            "token": session["token"],
            "pubkey": session["pubkey"],
        }
        with _lock:
            _lnurl_sessions.pop(k1, None)
        return result

    return {"status": "pending"}


def cleanup_expired() -> None:
    """Remove expired LNURL challenges."""
    now = time.time()
    with _lock:
        expired = [k for k, v in _lnurl_sessions.items() if now > v["expires_at"]]
        for k in expired:
            del _lnurl_sessions[k]
