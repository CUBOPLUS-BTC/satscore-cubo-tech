import secrets
import time
import threading

_sessions: dict[str, tuple[str, float]] = {}  # token -> (pubkey, expires_at)
_lock = threading.Lock()

SESSION_TTL = 86400 * 7  # 7 days


def create_session(pubkey: str) -> str:
    """Create a session token for an authenticated user."""
    token = secrets.token_hex(32)
    expires_at = time.time() + SESSION_TTL
    with _lock:
        _sessions[token] = (pubkey, expires_at)
    return token


def validate_session(token: str) -> str | None:
    """Return pubkey if token is valid, None otherwise."""
    with _lock:
        entry = _sessions.get(token)
    if entry is None:
        return None
    pubkey, expires_at = entry
    if time.time() > expires_at:
        with _lock:
            _sessions.pop(token, None)
        return None
    return pubkey


def cleanup_expired() -> None:
    """Remove all expired sessions. Call periodically."""
    now = time.time()
    with _lock:
        expired = [t for t, (_, exp) in _sessions.items() if now > exp]
        for t in expired:
            del _sessions[t]
