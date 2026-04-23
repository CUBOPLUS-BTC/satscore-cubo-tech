"""
tests/test_nostr.py
===================
Test suite covering Nostr protocol structures used by the Magma auth system.

Tests cover:
- Nostr event ID computation (NIP-01)
- Event JSON serialisation format
- NIP-19 bech32 encoding (npub, note)
- Challenge/response structure (kind 27235)
- NIP-98 HTTP Auth event structure
- Filter matching
- Relay message parsing
- Zap request/receipt structures
- Contact list (kind 3) parsing
- Session lifecycle

Test count: 33+
"""

import sys
import os
import json
import hashlib
import time
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.auth.bech32 import bech32_encode, lnurl_encode
from app.auth import sessions
from app.auth.nostr_verify import verify_nostr_event, verify_nip98_event


# ---------------------------------------------------------------------------
# Helpers: build well-formed Nostr events without real signatures
# ---------------------------------------------------------------------------

def _compute_event_id(pubkey: str, created_at: int, kind: int,
                      tags: list, content: str) -> str:
    """Compute the canonical NIP-01 event id (SHA256 of serialised event)."""
    serialized = json.dumps(
        [0, pubkey, created_at, kind, tags, content],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _make_auth_event(
    pubkey: str = "a" * 64,
    challenge: str = "test_challenge",
    kind: int = 27235,
    url: str = "https://api.eclalune.com/auth/verify",
    method: str = "POST",
    age_seconds: int = 0,
    sig: str = "b" * 128,
) -> dict:
    """Build a minimal NIP-98 / NIP-42 style auth event."""
    created_at = int(time.time()) - age_seconds
    tags = [
        ["u", url],
        ["method", method],
    ]
    event_id = _compute_event_id(pubkey, created_at, kind, tags, challenge)
    return {
        "id": event_id,
        "pubkey": pubkey,
        "created_at": created_at,
        "kind": kind,
        "tags": tags,
        "content": challenge,
        "sig": sig,
    }


def _make_text_note(
    pubkey: str = "a" * 64,
    content: str = "Hello Nostr",
    tags: list = None,
) -> dict:
    """Build a kind-1 text note."""
    tags = tags or []
    created_at = int(time.time())
    event_id = _compute_event_id(pubkey, created_at, 1, tags, content)
    return {
        "id": event_id,
        "pubkey": pubkey,
        "created_at": created_at,
        "kind": 1,
        "tags": tags,
        "content": content,
        "sig": "c" * 128,
    }


# ===========================================================================
# Event ID Computation
# ===========================================================================

class TestNostrEventId(unittest.TestCase):

    def test_event_id_is_64_hex_chars(self):
        eid = _compute_event_id("a" * 64, 1000000, 1, [], "hello")
        self.assertEqual(len(eid), 64)
        bytes.fromhex(eid)  # must be valid hex

    def test_event_id_changes_with_content(self):
        eid1 = _compute_event_id("a" * 64, 1000000, 1, [], "hello")
        eid2 = _compute_event_id("a" * 64, 1000000, 1, [], "world")
        self.assertNotEqual(eid1, eid2)

    def test_event_id_changes_with_pubkey(self):
        eid1 = _compute_event_id("a" * 64, 1000000, 1, [], "same")
        eid2 = _compute_event_id("b" * 64, 1000000, 1, [], "same")
        self.assertNotEqual(eid1, eid2)

    def test_event_id_changes_with_timestamp(self):
        eid1 = _compute_event_id("a" * 64, 1000000, 1, [], "same")
        eid2 = _compute_event_id("a" * 64, 1000001, 1, [], "same")
        self.assertNotEqual(eid1, eid2)

    def test_event_id_deterministic(self):
        args = ("a" * 64, 1000000, 1, [["e", "b" * 64]], "content")
        self.assertEqual(_compute_event_id(*args), _compute_event_id(*args))

    def test_event_id_matches_nip01_spec(self):
        # Verify the canonical serialisation order: [0, pubkey, created_at, kind, tags, content]
        pubkey = "a" * 64
        created_at = 1000000
        kind = 1
        tags = []
        content = ""
        serialized = json.dumps(
            [0, pubkey, created_at, kind, tags, content],
            separators=(",", ":"),
        )
        expected = hashlib.sha256(serialized.encode()).hexdigest()
        self.assertEqual(_compute_event_id(pubkey, created_at, kind, tags, content), expected)


# ===========================================================================
# Event JSON Structure
# ===========================================================================

class TestNostrEventStructure(unittest.TestCase):

    def test_text_note_has_required_fields(self):
        event = _make_text_note()
        for field in ["id", "pubkey", "created_at", "kind", "tags", "content", "sig"]:
            self.assertIn(field, event)

    def test_text_note_kind_is_1(self):
        event = _make_text_note()
        self.assertEqual(event["kind"], 1)

    def test_auth_event_kind_is_27235(self):
        event = _make_auth_event()
        self.assertEqual(event["kind"], 27235)

    def test_pubkey_is_64_hex(self):
        event = _make_text_note(pubkey="a" * 64)
        self.assertEqual(len(event["pubkey"]), 64)

    def test_sig_is_128_hex(self):
        event = _make_text_note()
        self.assertEqual(len(event["sig"]), 128)

    def test_tags_is_list(self):
        event = _make_text_note()
        self.assertIsInstance(event["tags"], list)

    def test_auth_event_has_u_and_method_tags(self):
        event = _make_auth_event()
        tag_dict = {t[0]: t[1:] for t in event["tags"]}
        self.assertIn("u", tag_dict)
        self.assertIn("method", tag_dict)

    def test_auth_event_url_tag(self):
        url = "https://api.example.com/auth"
        event = _make_auth_event(url=url)
        tag_dict = {t[0]: t[1] for t in event["tags"] if len(t) >= 2}
        self.assertEqual(tag_dict["u"], url)


# ===========================================================================
# verify_nostr_event
# ===========================================================================

class TestVerifyNostrEvent(unittest.TestCase):

    def test_wrong_kind_fails(self):
        event = _make_auth_event(kind=1)
        self.assertFalse(verify_nostr_event(event, "test_challenge"))

    def test_expired_event_fails(self):
        event = _make_auth_event(age_seconds=200)  # older than 120s TTL
        self.assertFalse(verify_nostr_event(event, "test_challenge"))

    def test_wrong_content_fails(self):
        event = _make_auth_event(challenge="correct_challenge")
        self.assertFalse(verify_nostr_event(event, "wrong_challenge"))

    def test_missing_u_tag_fails(self):
        event = _make_auth_event()
        # Remove the 'u' tag
        event["tags"] = [t for t in event["tags"] if t[0] != "u"]
        self.assertFalse(verify_nostr_event(event, event["content"]))

    def test_missing_method_tag_fails(self):
        event = _make_auth_event()
        event["tags"] = [t for t in event["tags"] if t[0] != "method"]
        self.assertFalse(verify_nostr_event(event, event["content"]))

    def test_id_mismatch_fails(self):
        event = _make_auth_event(challenge="test")
        event["id"] = "0" * 64  # tampered id
        self.assertFalse(verify_nostr_event(event, "test"))

    def test_valid_event_structure_but_invalid_sig(self):
        # The Schnorr verification will fail (no real key),
        # but all pre-checks should pass and only sig fails
        event = _make_auth_event(challenge="test_challenge")
        # With a fake sig, the Schnorr check fails — result is False
        result = verify_nostr_event(event, "test_challenge")
        self.assertFalse(result)


# ===========================================================================
# NIP-98 Verification
# ===========================================================================

class TestVerifyNip98(unittest.TestCase):

    def test_wrong_url_fails(self):
        url = "https://api.example.com/endpoint"
        event = _make_auth_event(url=url)
        self.assertFalse(verify_nip98_event(event, "https://different.com", "POST"))

    def test_wrong_method_fails(self):
        url = "https://api.example.com/endpoint"
        event = _make_auth_event(url=url, method="POST")
        self.assertFalse(verify_nip98_event(event, url, "GET"))

    def test_expired_nip98_fails(self):
        event = _make_auth_event(age_seconds=200)
        self.assertFalse(verify_nip98_event(event, "https://api.eclalune.com/auth/verify", "POST"))

    def test_id_mismatch_nip98_fails(self):
        url = "https://api.eclalune.com/auth/verify"
        event = _make_auth_event(url=url, challenge="")
        event["id"] = "f" * 64
        self.assertFalse(verify_nip98_event(event, url, "POST"))


# ===========================================================================
# NIP-19 bech32 encoding (npub, note, nprofile, nevent)
# ===========================================================================

class TestNip19Encoding(unittest.TestCase):
    """Validate that NIP-19 bech32 encoding produces the correct HRP prefixes.

    We use the app's own bech32 encoder (app.auth.bech32) and cross-check
    the output format.  We do NOT test against the app.btcprotocol bech32 encoder
    because NIP-19 uses Bech32 (not Bech32m or SegWit), which is distinct.
    """

    def test_npub_starts_with_npub1(self):
        # npub is bech32 encoding of raw 32-byte pubkey with HRP "npub"
        pubkey_bytes = bytes.fromhex("a" * 64)
        encoded = bech32_encode("npub", pubkey_bytes)
        self.assertTrue(encoded.startswith("npub1"))

    def test_note_starts_with_note1(self):
        note_id = bytes.fromhex("b" * 64)
        encoded = bech32_encode("note", note_id)
        self.assertTrue(encoded.startswith("note1"))

    def test_nsec_starts_with_nsec1(self):
        secret = bytes(32)
        encoded = bech32_encode("nsec", secret)
        self.assertTrue(encoded.startswith("nsec1"))

    def test_encoding_is_lowercase(self):
        pubkey_bytes = bytes(32)
        encoded = bech32_encode("npub", pubkey_bytes)
        self.assertEqual(encoded, encoded.lower())

    def test_different_pubkeys_different_encoding(self):
        enc1 = bech32_encode("npub", bytes(32))
        enc2 = bech32_encode("npub", bytes([1] * 32))
        self.assertNotEqual(enc1, enc2)


# ===========================================================================
# LNURL encoding
# ===========================================================================

class TestLnurlEncoding(unittest.TestCase):

    def test_lnurl_starts_with_lnurl1(self):
        url = "https://api.eclalune.com/lnurl/auth?tag=login&k1=abc"
        encoded = lnurl_encode(url)
        self.assertTrue(encoded.startswith("LNURL1"))

    def test_lnurl_is_uppercase(self):
        url = "https://example.com/lnurl"
        encoded = lnurl_encode(url)
        self.assertEqual(encoded, encoded.upper())

    def test_lnurl_deterministic(self):
        url = "https://api.eclalune.com/test"
        self.assertEqual(lnurl_encode(url), lnurl_encode(url))


# ===========================================================================
# Filter matching (NIP-01)
# ===========================================================================

class TestNostrFilterMatching(unittest.TestCase):
    """Test that events match/reject NIP-01 subscription filters correctly.

    We implement a minimal filter matching function here since the app
    doesn't expose one directly — this tests the logic that would live in a
    relay/client component.
    """

    def _matches_filter(self, event: dict, f: dict) -> bool:
        """Minimal NIP-01 filter matcher."""
        if "ids" in f:
            if event["id"] not in f["ids"]:
                return False
        if "authors" in f:
            if event["pubkey"] not in f["authors"]:
                return False
        if "kinds" in f:
            if event["kind"] not in f["kinds"]:
                return False
        if "since" in f:
            if event["created_at"] < f["since"]:
                return False
        if "until" in f:
            if event["created_at"] > f["until"]:
                return False
        if "#e" in f:
            e_tags = [t[1] for t in event.get("tags", []) if t[0] == "e"]
            if not any(eid in f["#e"] for eid in e_tags):
                return False
        if "#p" in f:
            p_tags = [t[1] for t in event.get("tags", []) if t[0] == "p"]
            if not any(pk in f["#p"] for pk in p_tags):
                return False
        return True

    def test_kind_filter_matches(self):
        event = _make_text_note()
        self.assertTrue(self._matches_filter(event, {"kinds": [1]}))

    def test_kind_filter_rejects(self):
        event = _make_text_note()
        self.assertFalse(self._matches_filter(event, {"kinds": [3, 7]}))

    def test_author_filter_matches(self):
        pubkey = "a" * 64
        event = _make_text_note(pubkey=pubkey)
        self.assertTrue(self._matches_filter(event, {"authors": [pubkey]}))

    def test_author_filter_rejects(self):
        event = _make_text_note(pubkey="a" * 64)
        self.assertFalse(self._matches_filter(event, {"authors": ["b" * 64]}))

    def test_since_filter(self):
        event = _make_text_note()
        future = event["created_at"] + 1000
        self.assertFalse(self._matches_filter(event, {"since": future}))
        past = event["created_at"] - 1000
        self.assertTrue(self._matches_filter(event, {"since": past}))

    def test_until_filter(self):
        event = _make_text_note()
        past = event["created_at"] - 1000
        self.assertFalse(self._matches_filter(event, {"until": past}))
        future = event["created_at"] + 1000
        self.assertTrue(self._matches_filter(event, {"until": future}))

    def test_e_tag_filter(self):
        target_id = "c" * 64
        event = _make_text_note(tags=[["e", target_id]])
        self.assertTrue(self._matches_filter(event, {"#e": [target_id]}))
        self.assertFalse(self._matches_filter(event, {"#e": ["d" * 64]}))

    def test_empty_filter_matches_all(self):
        event = _make_text_note()
        self.assertTrue(self._matches_filter(event, {}))


# ===========================================================================
# Relay Message Parsing
# ===========================================================================

class TestRelayMessageParsing(unittest.TestCase):
    """Validate parsing of NIP-01 relay messages."""

    def _parse_relay_msg(self, msg: str) -> tuple:
        """Parse a JSON relay message into (type, *args)."""
        parsed = json.loads(msg)
        if not isinstance(parsed, list) or not parsed:
            return ("UNKNOWN",)
        return tuple(parsed)

    def test_event_message(self):
        event = _make_text_note()
        msg = json.dumps(["EVENT", "sub1", event])
        parsed = self._parse_relay_msg(msg)
        self.assertEqual(parsed[0], "EVENT")
        self.assertEqual(parsed[1], "sub1")
        self.assertIsInstance(parsed[2], dict)

    def test_eose_message(self):
        msg = json.dumps(["EOSE", "sub1"])
        parsed = self._parse_relay_msg(msg)
        self.assertEqual(parsed[0], "EOSE")
        self.assertEqual(parsed[1], "sub1")

    def test_ok_message(self):
        msg = json.dumps(["OK", "a" * 64, True, ""])
        parsed = self._parse_relay_msg(msg)
        self.assertEqual(parsed[0], "OK")
        self.assertTrue(parsed[2])

    def test_notice_message(self):
        msg = json.dumps(["NOTICE", "Rate limit exceeded"])
        parsed = self._parse_relay_msg(msg)
        self.assertEqual(parsed[0], "NOTICE")
        self.assertIn("Rate", parsed[1])

    def test_auth_relay_message(self):
        msg = json.dumps(["AUTH", "challenge_string_xyz"])
        parsed = self._parse_relay_msg(msg)
        self.assertEqual(parsed[0], "AUTH")
        self.assertEqual(parsed[1], "challenge_string_xyz")


# ===========================================================================
# Zap Structures (NIP-57)
# ===========================================================================

class TestZapStructures(unittest.TestCase):
    """Validate the structure of NIP-57 zap requests and receipts."""

    def _make_zap_request(
        self,
        recipient_pubkey: str = "b" * 64,
        amount_msats: int = 1000,
        relays: list = None,
    ) -> dict:
        """Build a kind-9734 zap request event."""
        relays = relays or ["wss://relay.damus.io"]
        pubkey = "a" * 64
        created_at = int(time.time())
        tags = [
            ["p", recipient_pubkey],
            ["amount", str(amount_msats)],
            ["relays"] + relays,
        ]
        event_id = _compute_event_id(pubkey, created_at, 9734, tags, "")
        return {
            "id": event_id,
            "pubkey": pubkey,
            "created_at": created_at,
            "kind": 9734,
            "tags": tags,
            "content": "",
            "sig": "d" * 128,
        }

    def _make_zap_receipt(
        self,
        zap_request: dict,
        preimage: str = "e" * 64,
        bolt11: str = "lnbc1000n1...",
    ) -> dict:
        """Build a kind-9735 zap receipt event (issued by LNURL server)."""
        pubkey = "f" * 64  # LNURL server pubkey
        created_at = int(time.time())
        tags = [
            ["p", zap_request["pubkey"]],
            ["bolt11", bolt11],
            ["preimage", preimage],
            ["description", json.dumps(zap_request)],
        ]
        event_id = _compute_event_id(pubkey, created_at, 9735, tags, "")
        return {
            "id": event_id,
            "pubkey": pubkey,
            "created_at": created_at,
            "kind": 9735,
            "tags": tags,
            "content": "",
            "sig": "e" * 128,
        }

    def test_zap_request_kind_9734(self):
        req = self._make_zap_request()
        self.assertEqual(req["kind"], 9734)

    def test_zap_receipt_kind_9735(self):
        req = self._make_zap_request()
        receipt = self._make_zap_receipt(req)
        self.assertEqual(receipt["kind"], 9735)

    def test_zap_request_has_p_tag(self):
        recipient = "b" * 64
        req = self._make_zap_request(recipient_pubkey=recipient)
        p_tags = [t[1] for t in req["tags"] if t[0] == "p"]
        self.assertIn(recipient, p_tags)

    def test_zap_request_has_amount_tag(self):
        req = self._make_zap_request(amount_msats=21000)
        amount_tags = [t[1] for t in req["tags"] if t[0] == "amount"]
        self.assertIn("21000", amount_tags)

    def test_zap_receipt_has_bolt11_tag(self):
        req = self._make_zap_request()
        receipt = self._make_zap_receipt(req, bolt11="lnbc100n1test")
        bolt11_tags = [t[1] for t in receipt["tags"] if t[0] == "bolt11"]
        self.assertIn("lnbc100n1test", bolt11_tags)


# ===========================================================================
# Contact List (NIP-02, kind 3)
# ===========================================================================

class TestContactListParsing(unittest.TestCase):

    def _make_contact_list(self, contacts: list) -> dict:
        """Build a kind-3 contact list event.

        Parameters
        ----------
        contacts : list of (pubkey_hex, relay_url, petname)
        """
        pubkey = "a" * 64
        created_at = int(time.time())
        tags = [["p", pk, relay, name] for pk, relay, name in contacts]
        event_id = _compute_event_id(pubkey, created_at, 3, tags, "")
        return {
            "id": event_id,
            "pubkey": pubkey,
            "created_at": created_at,
            "kind": 3,
            "tags": tags,
            "content": "",
            "sig": "0" * 128,
        }

    def _extract_contacts(self, event: dict) -> list:
        return [
            {"pubkey": t[1], "relay": t[2] if len(t) > 2 else "", "name": t[3] if len(t) > 3 else ""}
            for t in event["tags"] if t[0] == "p"
        ]

    def test_contact_list_kind_3(self):
        cl = self._make_contact_list([("b" * 64, "wss://relay.damus.io", "alice")])
        self.assertEqual(cl["kind"], 3)

    def test_contact_count(self):
        contacts = [
            ("b" * 64, "wss://r1.io", "alice"),
            ("c" * 64, "wss://r2.io", "bob"),
        ]
        cl = self._make_contact_list(contacts)
        extracted = self._extract_contacts(cl)
        self.assertEqual(len(extracted), 2)

    def test_contact_pubkeys_correct(self):
        pk1, pk2 = "b" * 64, "c" * 64
        cl = self._make_contact_list([(pk1, "", ""), (pk2, "", "")])
        extracted = self._extract_contacts(cl)
        extracted_pks = {c["pubkey"] for c in extracted}
        self.assertIn(pk1, extracted_pks)
        self.assertIn(pk2, extracted_pks)

    def test_empty_contact_list(self):
        cl = self._make_contact_list([])
        self.assertEqual(len(self._extract_contacts(cl)), 0)


# ===========================================================================
# Session lifecycle
# ===========================================================================

class TestSessionLifecycle(unittest.TestCase):

    def setUp(self):
        # Clear sessions before each test by patching the module-level dict
        sessions._sessions.clear()

    def test_create_session_returns_64_hex_token(self):
        token = sessions.create_session("a" * 64)
        self.assertEqual(len(token), 64)
        bytes.fromhex(token)

    def test_validate_valid_session(self):
        pubkey = "b" * 64
        token = sessions.create_session(pubkey)
        result = sessions.validate_session(token)
        self.assertEqual(result, pubkey)

    def test_validate_invalid_token_returns_none(self):
        result = sessions.validate_session("nonexistent_token")
        self.assertIsNone(result)

    def test_session_token_is_unique(self):
        t1 = sessions.create_session("a" * 64)
        t2 = sessions.create_session("a" * 64)
        self.assertNotEqual(t1, t2)

    def test_cleanup_removes_expired(self):
        pubkey = "c" * 64
        token = sessions.create_session(pubkey)
        # Manually expire the session
        with sessions._lock:
            sessions._sessions[token] = (pubkey, time.time() - 1)
        sessions.cleanup_expired()
        self.assertIsNone(sessions.validate_session(token))

    def test_multiple_sessions_for_same_pubkey(self):
        pubkey = "d" * 64
        t1 = sessions.create_session(pubkey)
        t2 = sessions.create_session(pubkey)
        self.assertEqual(sessions.validate_session(t1), pubkey)
        self.assertEqual(sessions.validate_session(t2), pubkey)

    def test_expired_session_returns_none(self):
        pubkey = "e" * 64
        token = sessions.create_session(pubkey)
        # Force expiry
        with sessions._lock:
            sessions._sessions[token] = (pubkey, time.time() - 1)
        result = sessions.validate_session(token)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
