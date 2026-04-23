"""Tests for the auth module.

Covers:
- Session creation, validation, expiry, and cleanup
- LNURL challenge creation
- bech32 encoding helpers
- Challenge TTL enforcement
"""

import sys
import os
import time
import threading
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.auth.bech32 import bech32_encode, lnurl_encode
from app.auth import sessions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pubkey(char: str = "a") -> str:
    return char * 64


# ---------------------------------------------------------------------------
# bech32 encoding
# ---------------------------------------------------------------------------


class TestBech32Encode(unittest.TestCase):

    def test_encode_returns_string(self):
        result = bech32_encode("lnurl", b"https://example.com/auth")
        self.assertIsInstance(result, str)

    def test_encode_starts_with_hrp(self):
        result = bech32_encode("lnurl", b"https://example.com")
        self.assertTrue(result.startswith("lnurl1"))

    def test_encode_lowercase(self):
        result = bech32_encode("lnurl", b"data")
        self.assertEqual(result, result.lower())

    def test_encode_deterministic(self):
        data = b"https://api.example.com/auth/lnurl-callback?tag=login&k1=abc"
        r1 = bech32_encode("lnurl", data)
        r2 = bech32_encode("lnurl", data)
        self.assertEqual(r1, r2)

    def test_encode_different_data_different_result(self):
        r1 = bech32_encode("lnurl", b"hello")
        r2 = bech32_encode("lnurl", b"world")
        self.assertNotEqual(r1, r2)

    def test_encode_empty_bytes(self):
        result = bech32_encode("lnurl", b"")
        self.assertIsInstance(result, str)

    def test_lnurl_encode_uppercase(self):
        result = lnurl_encode("https://example.com/callback")
        self.assertEqual(result, result.upper())

    def test_lnurl_encode_starts_with_lnurl1(self):
        result = lnurl_encode("https://example.com/cb")
        self.assertTrue(result.startswith("LNURL1"))

    def test_lnurl_encode_long_url(self):
        url = "https://api.eclalune.com/auth/lnurl-callback?tag=login&k1=" + "f" * 64
        result = lnurl_encode(url)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_lnurl_encode_produces_valid_bech32_chars(self):
        # bech32 charset: qpzry9x8gf2tvdw0s3jn54khce6mua7l
        # After upper: QPZRY9X8GF2TVDW0S3JN54KHCE6MUA7L
        result = lnurl_encode("https://example.com")
        # Strip the HRP prefix "LNURL1"
        data_part = result[6:]
        valid_chars = set("QPZRY9X8GF2TVDW0S3JN54KHCE6MUA7L")
        for ch in data_part:
            self.assertIn(ch, valid_chars, f"Invalid char {ch!r} in lnurl")


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


class TestSessionCreation(unittest.TestCase):

    def setUp(self):
        # Clear all sessions before each test
        with sessions._lock:
            sessions._sessions.clear()

    def test_create_session_returns_string(self):
        token = sessions.create_session(_make_pubkey())
        self.assertIsInstance(token, str)

    def test_create_session_token_length(self):
        token = sessions.create_session(_make_pubkey())
        # secrets.token_hex(32) -> 64 chars
        self.assertEqual(len(token), 64)

    def test_create_session_unique_tokens(self):
        pubkey = _make_pubkey("b")
        t1 = sessions.create_session(pubkey)
        t2 = sessions.create_session(pubkey)
        self.assertNotEqual(t1, t2)

    def test_validate_session_returns_pubkey(self):
        pubkey = _make_pubkey("c")
        token = sessions.create_session(pubkey)
        result = sessions.validate_session(token)
        self.assertEqual(result, pubkey)

    def test_validate_nonexistent_token_returns_none(self):
        result = sessions.validate_session("0" * 64)
        self.assertIsNone(result)

    def test_validate_empty_token_returns_none(self):
        result = sessions.validate_session("")
        self.assertIsNone(result)

    def test_session_survives_before_expiry(self):
        pubkey = _make_pubkey("d")
        token = sessions.create_session(pubkey)
        # Well within TTL
        self.assertIsNotNone(sessions.validate_session(token))

    def test_expired_session_returns_none(self):
        pubkey = _make_pubkey("e")
        token = sessions.create_session(pubkey)
        # Manually set expiry to the past
        with sessions._lock:
            sessions._sessions[token] = (pubkey, time.time() - 1)
        result = sessions.validate_session(token)
        self.assertIsNone(result)

    def test_expired_session_is_removed(self):
        pubkey = _make_pubkey("f")
        token = sessions.create_session(pubkey)
        with sessions._lock:
            sessions._sessions[token] = (pubkey, time.time() - 1)
        sessions.validate_session(token)  # triggers removal
        with sessions._lock:
            self.assertNotIn(token, sessions._sessions)


class TestSessionCleanup(unittest.TestCase):

    def setUp(self):
        with sessions._lock:
            sessions._sessions.clear()

    def test_cleanup_removes_expired(self):
        pubkey = _make_pubkey()
        token = sessions.create_session(pubkey)
        with sessions._lock:
            sessions._sessions[token] = (pubkey, time.time() - 10)
        sessions.cleanup_expired()
        with sessions._lock:
            self.assertNotIn(token, sessions._sessions)

    def test_cleanup_keeps_valid(self):
        pubkey = _make_pubkey("a")
        token = sessions.create_session(pubkey)
        sessions.cleanup_expired()
        with sessions._lock:
            self.assertIn(token, sessions._sessions)

    def test_cleanup_mixed_sessions(self):
        p1, p2 = _make_pubkey("1"), _make_pubkey("2")
        t1 = sessions.create_session(p1)
        t2 = sessions.create_session(p2)
        with sessions._lock:
            sessions._sessions[t1] = (p1, time.time() - 1)
        sessions.cleanup_expired()
        with sessions._lock:
            self.assertNotIn(t1, sessions._sessions)
            self.assertIn(t2, sessions._sessions)


class TestLNURLChallenge(unittest.TestCase):

    def _mock_settings(self):
        mock = MagicMock()
        mock.PUBLIC_URL = "https://api.eclalune.com"
        return mock

    @patch("app.auth.lnurl.settings")
    def test_create_challenge_returns_dict(self, mock_settings):
        mock_settings.PUBLIC_URL = "https://api.eclalune.com"
        from app.auth.lnurl import create_lnurl_challenge
        result = create_lnurl_challenge()
        self.assertIsInstance(result, dict)

    @patch("app.auth.lnurl.settings")
    def test_create_challenge_has_k1(self, mock_settings):
        mock_settings.PUBLIC_URL = "https://api.eclalune.com"
        from app.auth.lnurl import create_lnurl_challenge
        result = create_lnurl_challenge()
        self.assertIn("k1", result)
        self.assertEqual(len(result["k1"]), 64)

    @patch("app.auth.lnurl.settings")
    def test_create_challenge_has_lnurl(self, mock_settings):
        mock_settings.PUBLIC_URL = "https://api.eclalune.com"
        from app.auth.lnurl import create_lnurl_challenge
        result = create_lnurl_challenge()
        self.assertIn("lnurl", result)
        self.assertTrue(result["lnurl"].startswith("LNURL1"))

    @patch("app.auth.lnurl.settings")
    def test_create_challenge_has_expires_at(self, mock_settings):
        mock_settings.PUBLIC_URL = "https://api.eclalune.com"
        from app.auth.lnurl import create_lnurl_challenge
        result = create_lnurl_challenge()
        self.assertIn("expires_at", result)
        # Should expire about 5 minutes from now
        self.assertGreater(result["expires_at"], int(time.time()))

    @patch("app.auth.lnurl.settings")
    def test_create_challenge_unique_k1s(self, mock_settings):
        mock_settings.PUBLIC_URL = "https://api.eclalune.com"
        from app.auth.lnurl import create_lnurl_challenge
        r1 = create_lnurl_challenge()
        r2 = create_lnurl_challenge()
        self.assertNotEqual(r1["k1"], r2["k1"])

    @patch("app.auth.lnurl.settings")
    def test_get_status_unknown_k1(self, mock_settings):
        mock_settings.PUBLIC_URL = "https://api.eclalune.com"
        from app.auth.lnurl import get_lnurl_status
        result = get_lnurl_status("deadbeef" * 8)
        self.assertEqual(result["status"], "error")

    @patch("app.auth.lnurl.settings")
    def test_get_status_pending(self, mock_settings):
        mock_settings.PUBLIC_URL = "https://api.eclalune.com"
        from app.auth.lnurl import create_lnurl_challenge, get_lnurl_status
        challenge = create_lnurl_challenge()
        status = get_lnurl_status(challenge["k1"])
        self.assertEqual(status["status"], "pending")

    @patch("app.auth.lnurl.settings")
    def test_challenge_cleanup_expired(self, mock_settings):
        mock_settings.PUBLIC_URL = "https://api.eclalune.com"
        from app.auth import lnurl as lnurl_mod
        challenge = lnurl_mod.create_lnurl_challenge()
        k1 = challenge["k1"]
        with lnurl_mod._lock:
            lnurl_mod._lnurl_sessions[k1]["expires_at"] = time.time() - 1
        lnurl_mod.cleanup_expired()
        with lnurl_mod._lock:
            self.assertNotIn(k1, lnurl_mod._lnurl_sessions)


class TestSessionConcurrency(unittest.TestCase):
    """Verify the lock protects _sessions under concurrent access."""

    def setUp(self):
        with sessions._lock:
            sessions._sessions.clear()

    def test_concurrent_create(self):
        results = []
        pubkey = _make_pubkey()

        def worker():
            token = sessions.create_session(pubkey)
            results.append(token)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results), 20)
        # All tokens should be unique
        self.assertEqual(len(set(results)), 20)


if __name__ == "__main__":
    unittest.main()
