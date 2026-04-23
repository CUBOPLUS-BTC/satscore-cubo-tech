"""
NIP (Nostr Implementation Possibilities) helpers.

Covers:
  NIP-01  Canonical serialisation & event ID
  NIP-02  Contact lists
  NIP-05  DNS-based verification
  NIP-10  Reply threading
  NIP-13  Proof of Work
  NIP-19  Bech32-encoded entities (npub, nsec, note, nprofile, nevent, naddr)
  NIP-25  Reactions
  NIP-36  Sensitive content
  NIP-40  Event expiration
  NIP-57  Lightning Zaps
  NIP-65  Relay list metadata

Pure Python standard library.
"""

import json
import time
import math
import hashlib
import re
import struct
from typing import List, Optional, Dict, Any, Tuple

# ---------------------------------------------------------------------------
# Bech32 implementation (per BIP-173, adapted for Nostr TLV entities)
# ---------------------------------------------------------------------------

_BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_BECH32_GENERATOR = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]


def _bech32_polymod(values):
    chk = 1
    for v in values:
        b = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ v
        for i in range(5):
            chk ^= _BECH32_GENERATOR[i] if ((b >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp):
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _bech32_create_checksum(hrp, data):
    values = _bech32_hrp_expand(hrp) + list(data)
    polymod = _bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def _bech32_verify_checksum(hrp, data):
    return _bech32_polymod(_bech32_hrp_expand(hrp) + list(data)) == 1


def _bech32_encode(hrp: str, data: bytes) -> str:
    """Encode bytes to bech32 string with given human-readable part."""
    converted = _convertbits(list(data), 8, 5)
    checksum = _bech32_create_checksum(hrp, converted)
    return hrp + "1" + "".join(_BECH32_CHARSET[d] for d in converted + checksum)


def _bech32_decode(bech32str: str) -> Tuple[str, bytes]:
    """Decode a bech32 string. Returns (hrp, raw_bytes)."""
    bech32str = bech32str.lower()
    if "1" not in bech32str:
        raise ValueError(f"Invalid bech32 string: {bech32str!r}")
    sep = bech32str.rfind("1")
    hrp = bech32str[:sep]
    data_part = bech32str[sep + 1 :]
    decoded = []
    for c in data_part:
        idx = _BECH32_CHARSET.find(c)
        if idx < 0:
            raise ValueError(f"Invalid character in bech32: {c!r}")
        decoded.append(idx)
    if not _bech32_verify_checksum(hrp, decoded):
        raise ValueError("Bech32 checksum verification failed")
    converted = _convertbits(decoded[:-6], 5, 8, pad=False)
    return hrp, bytes(converted)


def _convertbits(data, frombits, tobits, pad=True):
    """General power-of-2 base conversion."""
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            raise ValueError(f"Invalid value in convertbits: {value!r}")
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        raise ValueError("Invalid padding in convertbits")
    return ret


# ---------------------------------------------------------------------------
# NIP-01 Canonical serialisation
# ---------------------------------------------------------------------------

def serialize_event(event: dict) -> str:
    """
    NIP-01 canonical JSON serialisation.

    [0, pubkey, created_at, kind, tags, content]
    No extra whitespace.
    """
    return json.dumps(
        [
            0,
            event["pubkey"],
            event["created_at"],
            event["kind"],
            event["tags"],
            event["content"],
        ],
        separators=(",", ":"),
        ensure_ascii=False,
    )


def compute_event_id(event: dict) -> str:
    """Compute the NIP-01 event ID (SHA-256 of canonical serialisation)."""
    serialised = serialize_event(event)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# NIP-02 Contact List
# ---------------------------------------------------------------------------

def parse_contact_list(event: dict) -> List[Dict]:
    """
    Parse a kind-3 contact list event.

    Returns
    -------
    list of dicts: {pubkey, relay, petname}
    """
    if event.get("kind") != 3:
        raise ValueError(f"Expected kind 3, got {event.get('kind')}")
    contacts = []
    for tag in event.get("tags", []):
        if not tag or tag[0] != "p":
            continue
        contacts.append({
            "pubkey": tag[1] if len(tag) > 1 else "",
            "relay": tag[2] if len(tag) > 2 else "",
            "petname": tag[3] if len(tag) > 3 else "",
        })
    return contacts


def build_contact_list(contacts: list) -> dict:
    """
    Build the tags for a kind-3 contact list event.

    Parameters
    ----------
    contacts : list of dicts with 'pubkey', optionally 'relay' and 'petname'

    Returns
    -------
    dict with 'tags' key ready to include in an event
    """
    tags = []
    for c in contacts:
        tag = ["p", c["pubkey"]]
        relay = c.get("relay", "")
        petname = c.get("petname", "")
        if relay or petname:
            tag.append(relay)
        if petname:
            tag.append(petname)
        tags.append(tag)
    return {"tags": tags, "content": ""}


def merge_contact_lists(lists: List[List[dict]]) -> List[dict]:
    """
    Merge multiple contact lists, deduplicating by pubkey (last one wins).

    Parameters
    ----------
    lists : list of contact lists (each is a list of contact dicts)

    Returns
    -------
    deduplicated list of contact dicts
    """
    merged: Dict[str, dict] = {}
    for contact_list in lists:
        for contact in contact_list:
            pk = contact.get("pubkey", "")
            if pk:
                merged[pk] = contact
    return list(merged.values())


# ---------------------------------------------------------------------------
# NIP-05 DNS Verification
# ---------------------------------------------------------------------------

_NIP05_RE = re.compile(r"^([a-zA-Z0-9._-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})$")


def parse_nip05(identifier: str) -> Tuple[str, str]:
    """
    Split a NIP-05 identifier "name@domain" into (name, domain).

    Returns
    -------
    (name: str, domain: str)

    Raises
    ------
    ValueError if format is invalid
    """
    m = _NIP05_RE.match(identifier)
    if not m:
        raise ValueError(f"Invalid NIP-05 identifier: {identifier!r}")
    return m.group(1), m.group(2)


def build_nip05_json(
    names: Dict[str, str],
    relays: Dict[str, List[str]] = None,
) -> dict:
    """
    Build a .well-known/nostr.json document.

    Parameters
    ----------
    names  : dict mapping name -> hex pubkey
    relays : optional dict mapping hex pubkey -> list of relay URLs

    Returns
    -------
    dict ready to be JSON-serialised and served at /.well-known/nostr.json
    """
    doc = {"names": names}
    if relays:
        doc["relays"] = relays
    return doc


def validate_nip05_format(identifier: str) -> bool:
    """Return True if identifier matches the NIP-05 name@domain format."""
    return bool(_NIP05_RE.match(identifier))


# ---------------------------------------------------------------------------
# NIP-10 Reply Threading
# ---------------------------------------------------------------------------

def parse_thread_tags(tags: list) -> dict:
    """
    Parse NIP-10 threading tags from an event's tag list.

    Returns
    -------
    dict with:
        'root'     : {event_id, relay} or None
        'reply'    : {event_id, relay} or None
        'mentions' : list of {event_id, relay}
    """
    root = None
    reply = None
    mentions = []

    # New-style: tagged with positional markers
    for tag in tags:
        if not tag or tag[0] != "e":
            continue
        event_id = tag[1] if len(tag) > 1 else ""
        relay = tag[2] if len(tag) > 2 else ""
        marker = tag[3] if len(tag) > 3 else ""

        entry = {"event_id": event_id, "relay": relay}

        if marker == "root":
            root = entry
        elif marker == "reply":
            reply = entry
        elif marker == "mention":
            mentions.append(entry)
        else:
            # Deprecated positional style: first = root, last = reply
            mentions.append(entry)

    # Fallback: deprecated positional style
    e_tags = [tag for tag in tags if tag and tag[0] == "e"]
    if not any(len(t) > 3 for t in e_tags):
        # No markers — use positional convention
        if len(e_tags) == 1:
            reply = {"event_id": e_tags[0][1], "relay": e_tags[0][2] if len(e_tags[0]) > 2 else ""}
            mentions = []
        elif len(e_tags) >= 2:
            root = {"event_id": e_tags[0][1], "relay": e_tags[0][2] if len(e_tags[0]) > 2 else ""}
            reply = {"event_id": e_tags[-1][1], "relay": e_tags[-1][2] if len(e_tags[-1]) > 2 else ""}
            mentions = [
                {"event_id": t[1], "relay": t[2] if len(t) > 2 else ""}
                for t in e_tags[1:-1]
            ]

    return {"root": root, "reply": reply, "mentions": mentions}


def build_reply_tags(
    root_id: str,
    reply_to_id: str,
    mentions: List[str] = None,
    relays: Dict[str, str] = None,
) -> list:
    """
    Build NIP-10 compliant reply tags.

    Parameters
    ----------
    root_id    : str  — event ID of the thread root
    reply_to_id: str  — event ID being directly replied to
    mentions   : list of str  — additional event IDs to mention
    relays     : dict mapping event_id -> relay hint

    Returns
    -------
    list of tag arrays
    """
    relays = relays or {}
    tags = []

    if root_id == reply_to_id:
        tags.append(["e", root_id, relays.get(root_id, ""), "root"])
    else:
        tags.append(["e", root_id, relays.get(root_id, ""), "root"])
        tags.append(["e", reply_to_id, relays.get(reply_to_id, ""), "reply"])

    for event_id in (mentions or []):
        tags.append(["e", event_id, relays.get(event_id, ""), "mention"])

    return tags


def get_thread_depth(tags: list) -> int:
    """
    Estimate the reply depth from tags.

    Returns
    -------
    int  — 0 for root posts, 1 for direct replies, etc.
    """
    thread = parse_thread_tags(tags)
    if thread["root"] and thread["reply"]:
        return 2
    if thread["reply"]:
        return 1
    if thread["root"]:
        return 1
    e_count = sum(1 for tag in tags if tag and tag[0] == "e")
    return e_count


# ---------------------------------------------------------------------------
# NIP-13 Proof of Work
# ---------------------------------------------------------------------------

def count_leading_zero_bits(hex_id: str) -> int:
    """
    Count leading zero bits in a hex-encoded event ID.

    Parameters
    ----------
    hex_id : str  — 64-char lowercase hex string

    Returns
    -------
    int  — number of leading zero bits
    """
    count = 0
    for char in hex_id:
        nibble = int(char, 16)
        if nibble == 0:
            count += 4
        else:
            # Count leading zeros in this nibble
            for bit in range(3, -1, -1):
                if not (nibble >> bit & 1):
                    count += 1
                else:
                    return count
            return count
    return count


def meets_difficulty(event_id: str, difficulty: int) -> bool:
    """Return True if event_id has at least `difficulty` leading zero bits."""
    return count_leading_zero_bits(event_id) >= difficulty


def mine_event(
    event: dict,
    difficulty: int,
    max_attempts: int = 1_000_000,
) -> dict:
    """
    Mine an event by incrementing a nonce tag until the required PoW difficulty is met.

    Parameters
    ----------
    event       : dict  — event dict (will be copied; original not mutated)
    difficulty  : int   — minimum leading zero bits required
    max_attempts: int   — maximum iterations before raising

    Returns
    -------
    dict  — event dict with updated nonce tag and new ID

    Raises
    ------
    ValueError if difficulty not met within max_attempts
    """
    import copy
    e = copy.deepcopy(event)

    # Remove any existing nonce tag
    e["tags"] = [t for t in e.get("tags", []) if not (t and t[0] == "nonce")]

    for nonce in range(max_attempts):
        e["tags"].append(["nonce", str(nonce), str(difficulty)])
        event_id = compute_event_id(e)
        if meets_difficulty(event_id, difficulty):
            e["id"] = event_id
            return e
        e["tags"].pop()  # remove nonce tag to retry

    raise ValueError(
        f"Could not mine event to difficulty {difficulty} in {max_attempts} attempts"
    )


# ---------------------------------------------------------------------------
# NIP-19 Bech32-encoded entities
# ---------------------------------------------------------------------------

# TLV type bytes for nprofile, nevent, naddr
_TLV_SPECIAL  = 0  # hex data
_TLV_RELAY    = 1  # UTF-8 relay URL
_TLV_AUTHOR   = 2  # 32-byte pubkey
_TLV_KIND     = 3  # 4-byte big-endian uint32


def _encode_tlv(entries: list) -> bytes:
    """
    Encode a list of (type, value_bytes) tuples into TLV bytes.
    """
    buf = b""
    for typ, value in entries:
        if isinstance(value, str):
            value = value.encode("utf-8")
        buf += bytes([typ, len(value)]) + value
    return buf


def _decode_tlv(data: bytes) -> list:
    """
    Decode TLV bytes into a list of (type, value_bytes) tuples.
    """
    result = []
    i = 0
    while i < len(data):
        if i + 1 >= len(data):
            break
        typ = data[i]
        length = data[i + 1]
        value = data[i + 2 : i + 2 + length]
        result.append((typ, value))
        i += 2 + length
    return result


def encode_npub(pubkey_hex: str) -> str:
    """Encode a 32-byte hex pubkey to an npub1... bech32 string."""
    return _bech32_encode("npub", bytes.fromhex(pubkey_hex))


def decode_npub(npub: str) -> str:
    """Decode an npub1... bech32 string to a 64-char hex pubkey."""
    hrp, data = _bech32_decode(npub)
    if hrp != "npub":
        raise ValueError(f"Expected 'npub' HRP, got '{hrp}'")
    return data.hex()


def encode_note(event_id_hex: str) -> str:
    """Encode a 32-byte hex event ID to a note1... bech32 string."""
    return _bech32_encode("note", bytes.fromhex(event_id_hex))


def decode_note(note: str) -> str:
    """Decode a note1... bech32 string to a 64-char hex event ID."""
    hrp, data = _bech32_decode(note)
    if hrp != "note":
        raise ValueError(f"Expected 'note' HRP, got '{hrp}'")
    return data.hex()


def encode_nprofile(pubkey: str, relays: List[str] = None) -> str:
    """
    Encode an nprofile TLV entity with optional relay hints.

    Parameters
    ----------
    pubkey : str  — 64-char hex pubkey
    relays : list of str  — relay URLs

    Returns
    -------
    str  — nprofile1... bech32 string
    """
    entries = [(_TLV_SPECIAL, bytes.fromhex(pubkey))]
    for relay in (relays or []):
        entries.append((_TLV_RELAY, relay.encode("utf-8")))
    return _bech32_encode("nprofile", _encode_tlv(entries))


def decode_nprofile(nprofile: str) -> dict:
    """
    Decode an nprofile1... bech32 string.

    Returns
    -------
    dict with 'pubkey' and 'relays'
    """
    hrp, data = _bech32_decode(nprofile)
    if hrp != "nprofile":
        raise ValueError(f"Expected 'nprofile' HRP, got '{hrp}'")
    tlv = _decode_tlv(data)
    pubkey = ""
    relays = []
    for typ, value in tlv:
        if typ == _TLV_SPECIAL:
            pubkey = value.hex()
        elif typ == _TLV_RELAY:
            relays.append(value.decode("utf-8"))
    return {"pubkey": pubkey, "relays": relays}


def encode_nevent(
    event_id: str,
    relays: List[str] = None,
    author: str = None,
    kind: int = None,
) -> str:
    """
    Encode an nevent TLV entity.

    Parameters
    ----------
    event_id : str  — 64-char hex event ID
    relays   : list of relay URL strings
    author   : str  — optional 64-char hex pubkey
    kind     : int  — optional event kind

    Returns
    -------
    str  — nevent1... bech32 string
    """
    entries = [(_TLV_SPECIAL, bytes.fromhex(event_id))]
    for relay in (relays or []):
        entries.append((_TLV_RELAY, relay.encode("utf-8")))
    if author:
        entries.append((_TLV_AUTHOR, bytes.fromhex(author)))
    if kind is not None:
        entries.append((_TLV_KIND, struct.pack(">I", kind)))
    return _bech32_encode("nevent", _encode_tlv(entries))


def decode_nevent(nevent: str) -> dict:
    """
    Decode an nevent1... bech32 string.

    Returns
    -------
    dict with 'event_id', 'relays', 'author', 'kind'
    """
    hrp, data = _bech32_decode(nevent)
    if hrp != "nevent":
        raise ValueError(f"Expected 'nevent' HRP, got '{hrp}'")
    tlv = _decode_tlv(data)
    result = {"event_id": "", "relays": [], "author": None, "kind": None}
    for typ, value in tlv:
        if typ == _TLV_SPECIAL:
            result["event_id"] = value.hex()
        elif typ == _TLV_RELAY:
            result["relays"].append(value.decode("utf-8"))
        elif typ == _TLV_AUTHOR:
            result["author"] = value.hex()
        elif typ == _TLV_KIND:
            result["kind"] = struct.unpack(">I", value)[0]
    return result


def encode_naddr(
    identifier: str,
    pubkey: str,
    kind: int,
    relays: List[str] = None,
) -> str:
    """
    Encode an naddr TLV entity for parameterized replaceable events.

    Parameters
    ----------
    identifier : str  — 'd' tag value
    pubkey     : str  — 64-char hex pubkey
    kind       : int  — event kind (30000-39999)
    relays     : list of relay URLs

    Returns
    -------
    str  — naddr1... bech32 string
    """
    entries = [
        (_TLV_SPECIAL, identifier.encode("utf-8")),
        (_TLV_AUTHOR, bytes.fromhex(pubkey)),
        (_TLV_KIND, struct.pack(">I", kind)),
    ]
    for relay in (relays or []):
        entries.append((_TLV_RELAY, relay.encode("utf-8")))
    return _bech32_encode("naddr", _encode_tlv(entries))


def decode_naddr(naddr: str) -> dict:
    """
    Decode an naddr1... bech32 string.

    Returns
    -------
    dict with 'identifier', 'pubkey', 'kind', 'relays'
    """
    hrp, data = _bech32_decode(naddr)
    if hrp != "naddr":
        raise ValueError(f"Expected 'naddr' HRP, got '{hrp}'")
    tlv = _decode_tlv(data)
    result = {"identifier": "", "pubkey": "", "kind": None, "relays": []}
    for typ, value in tlv:
        if typ == _TLV_SPECIAL:
            result["identifier"] = value.decode("utf-8")
        elif typ == _TLV_AUTHOR:
            result["pubkey"] = value.hex()
        elif typ == _TLV_KIND:
            result["kind"] = struct.unpack(">I", value)[0]
        elif typ == _TLV_RELAY:
            result["relays"].append(value.decode("utf-8"))
    return result


# ---------------------------------------------------------------------------
# NIP-25 Reactions
# ---------------------------------------------------------------------------

REACTION_TYPES: Dict[str, str] = {
    "+": "like",
    "-": "dislike",
    "🤙": "shaka / love it",
    "❤️": "heart",
    "🔥": "fire",
    "👍": "thumbs up",
    "👎": "thumbs down",
    "😂": "laughing",
    "🎉": "celebration",
    "⚡": "zap / lightning",
    "🍊": "orange pill (Bitcoin)",
    "₿": "bitcoin",
    "🫂": "hug",
    "🙏": "prayer / thank you",
}


def parse_reaction(event: dict) -> dict:
    """
    Parse a kind-7 reaction event.

    Returns
    -------
    dict with 'content', 'reaction_type', 'target_event', 'target_author'
    """
    content = event.get("content", "+")
    tags = event.get("tags", [])

    target_event = None
    target_author = None

    # Last 'e' and 'p' tags per NIP-25
    e_tags = [t for t in tags if t and t[0] == "e"]
    p_tags = [t for t in tags if t and t[0] == "p"]

    if e_tags:
        last_e = e_tags[-1]
        target_event = {
            "event_id": last_e[1] if len(last_e) > 1 else "",
            "relay": last_e[2] if len(last_e) > 2 else "",
        }

    if p_tags:
        last_p = p_tags[-1]
        target_author = last_p[1] if len(last_p) > 1 else ""

    return {
        "content": content,
        "reaction_type": REACTION_TYPES.get(content, "custom"),
        "target_event": target_event,
        "target_author": target_author,
    }


def build_reaction(
    target_event_id: str,
    target_pubkey: str,
    content: str = "+",
    target_relay: str = "",
) -> dict:
    """
    Build a kind-7 reaction event dict (without id/sig).

    Returns
    -------
    dict with kind, content, tags
    """
    tags = [
        ["e", target_event_id, target_relay],
        ["p", target_pubkey],
    ]
    return {
        "kind": 7,
        "content": content,
        "tags": tags,
    }


# ---------------------------------------------------------------------------
# NIP-36 Sensitive Content
# ---------------------------------------------------------------------------

def mark_sensitive(event: dict, reason: str = "") -> dict:
    """
    Add a content-warning tag to an event dict.

    Returns a modified copy.
    """
    import copy
    e = copy.deepcopy(event)
    tag = ["content-warning"]
    if reason:
        tag.append(reason)
    e.setdefault("tags", []).append(tag)
    return e


def is_sensitive(event: dict) -> bool:
    """Return True if the event has a content-warning tag."""
    tags = event.get("tags", [])
    return any(t and t[0] == "content-warning" for t in tags)


# ---------------------------------------------------------------------------
# NIP-40 Event Expiration
# ---------------------------------------------------------------------------

def set_expiration(event: dict, timestamp: int) -> dict:
    """
    Add (or replace) an expiration tag on an event dict.

    Returns a modified copy.
    """
    import copy
    e = copy.deepcopy(event)
    e["tags"] = [t for t in e.get("tags", []) if not (t and t[0] == "expiration")]
    e["tags"].append(["expiration", str(timestamp)])
    return e


def get_expiration(event: dict) -> Optional[int]:
    """
    Return the expiration Unix timestamp from an event, or None if absent.
    """
    for tag in event.get("tags", []):
        if tag and tag[0] == "expiration" and len(tag) > 1:
            try:
                return int(tag[1])
            except (ValueError, TypeError):
                return None
    return None


def is_expired(event: dict) -> bool:
    """Return True if the event has expired (past its expiration timestamp)."""
    exp = get_expiration(event)
    if exp is None:
        return False
    return int(time.time()) > exp


# ---------------------------------------------------------------------------
# NIP-57 Lightning Zaps
# ---------------------------------------------------------------------------

def create_zap_request(
    sender_pubkey: str,
    recipient_pubkey: str,
    amount_msats: int,
    relays: List[str],
    event_id: str = None,
    comment: str = "",
    lnurl: str = "",
) -> dict:
    """
    Create a kind-9734 zap request event (sent to LNURL server).

    Parameters
    ----------
    sender_pubkey    : str  — sender's 64-char hex pubkey
    recipient_pubkey : str  — recipient's 64-char hex pubkey
    amount_msats     : int  — amount in millisatoshis
    relays           : list of str  — relay hints
    event_id         : str  — optional: zap a specific event
    comment          : str  — optional user comment
    lnurl            : str  — LNURL being zapped

    Returns
    -------
    dict  — unsigned zap request event (needs id computed and sig added)
    """
    tags = [
        ["p", recipient_pubkey],
        ["amount", str(amount_msats)],
        ["relays", *relays],
    ]
    if event_id:
        tags.append(["e", event_id])
    if lnurl:
        tags.append(["lnurl", lnurl])

    return {
        "kind": 9734,
        "pubkey": sender_pubkey,
        "content": comment,
        "tags": tags,
        "created_at": int(time.time()),
    }


def validate_zap_request(event: dict) -> Tuple[bool, List[str]]:
    """
    Validate a zap request event per NIP-57.

    Returns
    -------
    (is_valid: bool, errors: list of str)
    """
    errors = []

    if event.get("kind") != 9734:
        errors.append(f"Expected kind 9734, got {event.get('kind')}")

    tags = event.get("tags", [])
    p_tags = [t for t in tags if t and t[0] == "p"]
    amount_tags = [t for t in tags if t and t[0] == "amount"]

    if not p_tags:
        errors.append("Missing 'p' (recipient) tag")
    elif not re.fullmatch(r"[0-9a-f]{64}", p_tags[0][1] if len(p_tags[0]) > 1 else ""):
        errors.append("Invalid pubkey in 'p' tag")

    if not amount_tags:
        errors.append("Missing 'amount' tag")
    else:
        try:
            amount = int(amount_tags[0][1])
            if amount <= 0:
                errors.append("amount must be positive")
        except (ValueError, IndexError):
            errors.append("Invalid 'amount' tag value")

    if not event.get("pubkey"):
        errors.append("Missing sender pubkey")

    return len(errors) == 0, errors


def parse_zap_receipt(event: dict) -> dict:
    """
    Parse a kind-9735 zap receipt event.

    Returns
    -------
    dict with amount_msats, sender_pubkey, recipient_pubkey,
         zapped_event_id, bolt11, preimage, zap_request
    """
    if event.get("kind") != 9735:
        raise ValueError(f"Expected kind 9735, got {event.get('kind')}")

    tags = event.get("tags", [])
    result = {
        "amount_msats": None,
        "sender_pubkey": None,
        "recipient_pubkey": None,
        "zapped_event_id": None,
        "bolt11": None,
        "preimage": None,
        "zap_request": None,
    }

    for tag in tags:
        if not tag:
            continue
        if tag[0] == "p" and len(tag) > 1:
            result["recipient_pubkey"] = tag[1]
        elif tag[0] == "e" and len(tag) > 1:
            result["zapped_event_id"] = tag[1]
        elif tag[0] == "bolt11" and len(tag) > 1:
            result["bolt11"] = tag[1]
        elif tag[0] == "preimage" and len(tag) > 1:
            result["preimage"] = tag[1]
        elif tag[0] == "description" and len(tag) > 1:
            try:
                zap_req = json.loads(tag[1])
                result["zap_request"] = zap_req
                # Extract amount from zap request tags
                for ztag in zap_req.get("tags", []):
                    if ztag and ztag[0] == "amount" and len(ztag) > 1:
                        result["amount_msats"] = int(ztag[1])
                result["sender_pubkey"] = zap_req.get("pubkey")
            except (json.JSONDecodeError, ValueError):
                pass

    return result


def validate_zap_receipt(receipt: dict, request: dict) -> bool:
    """
    Basic validation that a zap receipt corresponds to a zap request.

    Checks:
    - recipient pubkey matches
    - bolt11 is present
    - description contains the original request

    Returns
    -------
    bool
    """
    if not receipt.get("bolt11"):
        return False

    zap_req = receipt.get("zap_request")
    if not zap_req:
        return False

    # Verify recipient pubkey matches
    req_p_tags = [t for t in request.get("tags", []) if t and t[0] == "p"]
    rec_p_tags = [t for t in receipt.get("tags", []) if t and t[0] == "p"]

    if req_p_tags and rec_p_tags:
        req_recipient = req_p_tags[0][1] if len(req_p_tags[0]) > 1 else ""
        rec_recipient = rec_p_tags[0][1] if len(rec_p_tags[0]) > 1 else ""
        if req_recipient != rec_recipient:
            return False

    return True


def get_zap_amount(receipt: dict) -> int:
    """
    Extract the zap amount in millisatoshis from a parsed receipt.

    Returns
    -------
    int  — amount in msats (0 if not found)
    """
    if isinstance(receipt, dict):
        if "amount_msats" in receipt and receipt["amount_msats"]:
            return int(receipt["amount_msats"])
        # Try raw event format
        tags = receipt.get("tags", [])
        for tag in tags:
            if tag and tag[0] == "amount" and len(tag) > 1:
                try:
                    return int(tag[1])
                except ValueError:
                    pass
    return 0


# ---------------------------------------------------------------------------
# NIP-65 Relay List Metadata
# ---------------------------------------------------------------------------

def parse_relay_list(event: dict) -> Dict[str, Dict[str, bool]]:
    """
    Parse a kind-10002 relay list metadata event.

    Returns
    -------
    dict mapping relay_url -> {'read': bool, 'write': bool}
    """
    if event.get("kind") != 10002:
        raise ValueError(f"Expected kind 10002, got {event.get('kind')}")

    relays: Dict[str, Dict[str, bool]] = {}
    for tag in event.get("tags", []):
        if not tag or tag[0] != "r":
            continue
        url = tag[1] if len(tag) > 1 else ""
        if not url:
            continue
        marker = tag[2] if len(tag) > 2 else ""
        if marker == "read":
            relays[url] = {"read": True, "write": False}
        elif marker == "write":
            relays[url] = {"read": False, "write": True}
        else:
            relays[url] = {"read": True, "write": True}

    return relays


def build_relay_list(relays: Dict[str, Dict[str, bool]]) -> dict:
    """
    Build a kind-10002 relay list event dict.

    Parameters
    ----------
    relays : dict mapping url -> {'read': bool, 'write': bool}

    Returns
    -------
    dict with 'kind', 'tags', 'content'
    """
    tags = []
    for url, perms in relays.items():
        read = perms.get("read", True)
        write = perms.get("write", True)
        if read and write:
            tags.append(["r", url])
        elif read:
            tags.append(["r", url, "read"])
        elif write:
            tags.append(["r", url, "write"])

    return {"kind": 10002, "tags": tags, "content": ""}


def get_read_relays(relay_list: Dict[str, Dict[str, bool]]) -> List[str]:
    """Return URLs of relays marked for reading."""
    return [url for url, perms in relay_list.items() if perms.get("read")]


def get_write_relays(relay_list: Dict[str, Dict[str, bool]]) -> List[str]:
    """Return URLs of relays marked for writing."""
    return [url for url, perms in relay_list.items() if perms.get("write")]
