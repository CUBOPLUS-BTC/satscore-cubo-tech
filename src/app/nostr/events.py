"""
Nostr event kinds, event model, builder, and validator.

Implements NIP-01 canonical event structure plus kind constants from
NIPs 02, 04, 05, 09, 10, 13, 18, 23, 25, 36, 40, 42, 57, 65, 78, and others.

Pure Python standard library.
"""

import json
import time
import hashlib
import re
from typing import List, Optional, Dict, Any, Tuple

# ---------------------------------------------------------------------------
# Event Kind Constants
# ---------------------------------------------------------------------------

# NIP-01 core kinds
KIND_METADATA             = 0    # User metadata (profile)
KIND_TEXT_NOTE            = 1    # Short text note
KIND_RECOMMEND_RELAY      = 2    # Relay recommendation
KIND_CONTACTS             = 3    # Contact list (NIP-02)
KIND_ENCRYPTED_DM         = 4    # Encrypted direct message (NIP-04)
KIND_DELETE               = 5    # Event deletion (NIP-09)
KIND_REPOST               = 6    # Repost (NIP-18)
KIND_REACTION             = 7    # Reaction (NIP-25)
KIND_BADGE_AWARD          = 8    # Badge award (NIP-58)

# NIP-28 Public Chat
KIND_CHANNEL_CREATE       = 40   # Create public channel
KIND_CHANNEL_METADATA     = 41   # Channel metadata update
KIND_CHANNEL_MESSAGE      = 42   # Channel message
KIND_CHANNEL_HIDE         = 43   # Hide message
KIND_CHANNEL_MUTE         = 44   # Mute user in channel

# NIP-09 Extended
KIND_GENERIC_REPOST       = 16   # Generic repost of any event kind

# NIP-13 (PoW tagged)
KIND_POW_TEXT_NOTE        = 1    # same as text note; PoW is via nonce tag

# NIP-42 Authentication
KIND_AUTH                 = 22242  # Client authentication
KIND_HTTP_AUTH            = 27235  # HTTP authentication

# NIP-57 Lightning Zaps
KIND_ZAP_REQUEST          = 9734   # Zap request (sent to LNURL)
KIND_ZAP_RECEIPT          = 9735   # Zap receipt (published by wallet)

# NIP-84 Highlights
KIND_HIGHLIGHT            = 9802

# NIP-51 Lists
KIND_MUTE_LIST            = 10000  # Mute list (replaceable)
KIND_PIN_LIST             = 10001  # Pinned notes (replaceable)
KIND_RELAY_LIST           = 10002  # Relay list metadata (NIP-65, replaceable)
KIND_BOOKMARKS            = 10003  # Bookmarks (replaceable)
KIND_COMMUNITIES          = 10004  # Communities list (replaceable)
KIND_PUBLIC_CHATS         = 10005  # Joined public chat channels (replaceable)
KIND_BLOCKED_RELAYS       = 10006  # Blocked relays (replaceable)
KIND_SEARCH_RELAYS        = 10007  # Search relays (replaceable)
KIND_SIMPLE_GROUPS        = 10009  # Simple groups list (replaceable)
KIND_INTERESTS            = 10015  # Interests (replaceable)
KIND_EMOJIS               = 10030  # Emoji list (replaceable)
KIND_DM_RELAYS            = 10050  # DM relay hints (replaceable)

# NIP-38 User Statuses
KIND_USER_STATUS          = 30315  # Parameterized replaceable user status

# NIP-23 Long-form content
KIND_ARTICLE              = 30023  # Long-form article (parameterized replaceable)
KIND_DRAFT                = 30024  # Draft article

# NIP-99 Classifieds
KIND_CLASSIFIED           = 30402  # Classified listing (parameterized replaceable)
KIND_DRAFT_CLASSIFIED     = 30403

# NIP-15 Nostr Marketplace
KIND_STALL                = 30017  # Product stall (parameterized replaceable)
KIND_PRODUCT              = 30018  # Product listing (parameterized replaceable)

# NIP-78 Application-specific data
KIND_APP_SPECIFIC         = 30078  # Application-specific data (parameterized replaceable)

# NIP-94 File Metadata
KIND_FILE_METADATA        = 1063

# NIP-96 HTTP File Storage
KIND_HTTP_FILE_HEADER     = 10096

# NIP-7D Threads
KIND_THREAD               = 11    # Thread (NIP-7D proposal)

# NIP-1984 Reporting
KIND_REPORT               = 1984  # Report event (NIP-56)

# NIP-32 Labeling
KIND_LABEL                = 1985  # Label event

# NIP-89 Application Handlers
KIND_APP_HANDLER          = 31990  # Application handler recommendation
KIND_APP_RECOMMENDATION   = 31989  # Application recommendation

# NIP-53 Live Activities
KIND_LIVE_EVENT           = 30311  # Live activity (parameterized replaceable)
KIND_LIVE_CHAT_MSG        = 1311   # Live chat message

# NIP-72 Moderated Communities
KIND_COMMUNITY            = 34550  # Community definition
KIND_COMMUNITY_POST_APPROVAL = 4550  # Community post approval

# NIP-75 Zap Goals
KIND_ZAP_GOAL             = 9041

# NIP-90 Data Vending Machine
KIND_DVM_REQUEST          = 5000   # DVM job request (5000-5999 range)
KIND_DVM_RESULT           = 6000   # DVM job result (6000-6999 range)
KIND_DVM_FEEDBACK         = 7000   # DVM job feedback

# ---------------------------------------------------------------------------
# Human-readable kind names mapping
# ---------------------------------------------------------------------------

EVENT_KIND_NAMES: Dict[int, str] = {
    KIND_METADATA:               "User Metadata",
    KIND_TEXT_NOTE:              "Text Note",
    KIND_RECOMMEND_RELAY:        "Recommend Relay",
    KIND_CONTACTS:               "Contact List",
    KIND_ENCRYPTED_DM:           "Encrypted Direct Message",
    KIND_DELETE:                 "Event Deletion",
    KIND_REPOST:                 "Repost",
    KIND_REACTION:               "Reaction",
    KIND_BADGE_AWARD:            "Badge Award",
    KIND_THREAD:                 "Thread",
    KIND_GENERIC_REPOST:         "Generic Repost",
    KIND_CHANNEL_CREATE:         "Channel Create",
    KIND_CHANNEL_METADATA:       "Channel Metadata",
    KIND_CHANNEL_MESSAGE:        "Channel Message",
    KIND_CHANNEL_HIDE:           "Channel Hide Message",
    KIND_CHANNEL_MUTE:           "Channel Mute User",
    KIND_FILE_METADATA:          "File Metadata",
    KIND_AUTH:                   "Client Authentication",
    KIND_HTTP_AUTH:              "HTTP Authentication",
    KIND_ZAP_REQUEST:            "Zap Request",
    KIND_ZAP_RECEIPT:            "Zap Receipt",
    KIND_HIGHLIGHT:              "Highlight",
    KIND_MUTE_LIST:              "Mute List",
    KIND_PIN_LIST:               "Pin List",
    KIND_RELAY_LIST:             "Relay List Metadata",
    KIND_BOOKMARKS:              "Bookmarks",
    KIND_COMMUNITIES:            "Communities",
    KIND_PUBLIC_CHATS:           "Public Chat Channels",
    KIND_BLOCKED_RELAYS:         "Blocked Relays",
    KIND_SEARCH_RELAYS:          "Search Relays",
    KIND_SIMPLE_GROUPS:          "Simple Groups",
    KIND_INTERESTS:              "Interests",
    KIND_EMOJIS:                 "Emoji List",
    KIND_DM_RELAYS:              "DM Relay Hints",
    KIND_LIVE_CHAT_MSG:          "Live Chat Message",
    KIND_REPORT:                 "Report",
    KIND_LABEL:                  "Label",
    KIND_ZAP_GOAL:               "Zap Goal",
    KIND_DVM_REQUEST:            "Data Vending Machine Request",
    KIND_DVM_RESULT:             "Data Vending Machine Result",
    KIND_DVM_FEEDBACK:           "Data Vending Machine Feedback",
    KIND_USER_STATUS:            "User Status",
    KIND_ARTICLE:                "Long-form Article",
    KIND_DRAFT:                  "Draft Article",
    KIND_STALL:                  "Product Stall",
    KIND_PRODUCT:                "Product Listing",
    KIND_APP_SPECIFIC:           "Application-Specific Data",
    KIND_CLASSIFIED:             "Classified Listing",
    KIND_LIVE_EVENT:             "Live Event",
    KIND_COMMUNITY:              "Community Definition",
    KIND_COMMUNITY_POST_APPROVAL:"Community Post Approval",
    KIND_APP_HANDLER:            "Application Handler",
    KIND_APP_RECOMMENDATION:     "Application Recommendation",
    KIND_HTTP_FILE_HEADER:       "HTTP File Header",
}


def get_kind_name(kind: int) -> str:
    """Return human-readable name for a kind, or 'Unknown Kind N'."""
    return EVENT_KIND_NAMES.get(kind, f"Unknown Kind {kind}")


# ---------------------------------------------------------------------------
# NostrEvent
# ---------------------------------------------------------------------------

class NostrEvent:
    """
    Represents a Nostr protocol event as specified by NIP-01.

    Attributes
    ----------
    pubkey     : str  — 32-byte hex-encoded public key
    kind       : int  — event kind
    content    : str  — event content
    tags       : list — list of tag arrays
    created_at : int  — Unix timestamp (seconds)
    id         : str  — 32-byte hex SHA-256 of the canonical serialisation
    sig        : str  — 64-byte hex Schnorr signature (optional, set externally)
    """

    def __init__(
        self,
        pubkey: str,
        kind: int,
        content: str,
        tags: list = None,
        created_at: int = None,
        id: str = None,
        sig: str = None,
    ):
        self.pubkey = pubkey
        self.kind = kind
        self.content = content
        self.tags = tags or []
        self.created_at = created_at or int(time.time())
        self.id = id
        self.sig = sig

        if self.id is None:
            self.id = self.compute_id()

    def compute_id(self) -> str:
        """
        Compute the event ID as SHA-256 of the canonical serialisation.

        Canonical form: JSON array [0, pubkey, created_at, kind, tags, content]
        with no extra whitespace.
        """
        serialised = self.serialize()
        return hashlib.sha256(serialised.encode("utf-8")).hexdigest()

    def serialize(self) -> str:
        """
        Canonical JSON serialisation per NIP-01.
        [0, pubkey, created_at, kind, tags, content]
        """
        return json.dumps(
            [0, self.pubkey, self.created_at, self.kind, self.tags, self.content],
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate all required fields.

        Returns
        -------
        (is_valid: bool, errors: list of str)
        """
        errors = []

        # pubkey
        if not self.pubkey:
            errors.append("pubkey is required")
        elif not re.fullmatch(r"[0-9a-f]{64}", self.pubkey):
            errors.append(f"pubkey must be 64 hex chars, got: {self.pubkey!r}")

        # kind
        if not isinstance(self.kind, int) or self.kind < 0:
            errors.append(f"kind must be a non-negative integer, got: {self.kind!r}")

        # created_at
        if not isinstance(self.created_at, int) or self.created_at < 0:
            errors.append(f"created_at must be a non-negative integer")

        # tags
        if not isinstance(self.tags, list):
            errors.append("tags must be a list")
        else:
            for i, tag in enumerate(self.tags):
                if not isinstance(tag, list):
                    errors.append(f"tag[{i}] must be a list, got {type(tag).__name__}")
                elif not tag:
                    errors.append(f"tag[{i}] must not be empty")
                else:
                    for j, v in enumerate(tag):
                        if not isinstance(v, str):
                            errors.append(f"tag[{i}][{j}] must be a string")

        # content
        if not isinstance(self.content, str):
            errors.append("content must be a string")
        elif len(self.content) > 65535:
            errors.append(f"content exceeds 65535 chars ({len(self.content)})")

        # id
        if self.id:
            expected_id = self.compute_id()
            if self.id != expected_id:
                errors.append(f"id mismatch: stored={self.id!r}, computed={expected_id!r}")

        return len(errors) == 0, errors

    def is_ephemeral(self) -> bool:
        """Ephemeral events: kind 20000-29999 (not stored by relays)."""
        return 20000 <= self.kind <= 29999

    def is_replaceable(self) -> bool:
        """
        Replaceable events: kind 0, 3, or 10000-19999.
        Only the latest event from a pubkey for a given kind is kept.
        """
        return self.kind in (0, 3) or 10000 <= self.kind <= 19999

    def is_parameterized_replaceable(self) -> bool:
        """
        Parameterized replaceable events: kind 30000-39999.
        Keyed by (pubkey, kind, d-tag value).
        """
        return 30000 <= self.kind <= 39999

    def get_tag_values(self, tag_name: str) -> List[str]:
        """
        Extract the first value of all tags matching tag_name.

        Parameters
        ----------
        tag_name : str  — single-character tag identifier (e.g. 'e', 'p', 't')

        Returns
        -------
        list of str  — first value of each matching tag
        """
        return [
            tag[1]
            for tag in self.tags
            if isinstance(tag, list) and len(tag) >= 2 and tag[0] == tag_name
        ]

    def get_tag_full(self, tag_name: str) -> List[List[str]]:
        """Return full tag arrays matching tag_name."""
        return [tag for tag in self.tags if isinstance(tag, list) and tag and tag[0] == tag_name]

    def get_referenced_events(self) -> List[str]:
        """Extract all 'e' tag event IDs."""
        return self.get_tag_values("e")

    def get_referenced_pubkeys(self) -> List[str]:
        """Extract all 'p' tag pubkeys."""
        return self.get_tag_values("p")

    def get_identifier(self) -> Optional[str]:
        """Return 'd' tag value for parameterized replaceable events."""
        values = self.get_tag_values("d")
        return values[0] if values else None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pubkey": self.pubkey,
            "created_at": self.created_at,
            "kind": self.kind,
            "tags": self.tags,
            "content": self.content,
            "sig": self.sig or "",
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NostrEvent":
        """Reconstruct a NostrEvent from a dict (e.g. received from relay)."""
        event = cls(
            pubkey=data.get("pubkey", ""),
            kind=data.get("kind", 1),
            content=data.get("content", ""),
            tags=data.get("tags", []),
            created_at=data.get("created_at"),
            id=data.get("id"),
            sig=data.get("sig"),
        )
        return event

    def __repr__(self):
        return (
            f"<NostrEvent id={self.id[:8]}... "
            f"kind={self.kind} ({get_kind_name(self.kind)}) "
            f"pubkey={self.pubkey[:8]}...>"
        )


# ---------------------------------------------------------------------------
# EventBuilder
# ---------------------------------------------------------------------------

class EventBuilder:
    """
    Fluent builder for constructing NostrEvent objects.

    Usage
    -----
    event = (
        EventBuilder(pubkey="abcdef...")
        .text_note("Hello Nostr!")
        .add_hashtag("bitcoin")
        .build()
    )
    """

    def __init__(self, pubkey: str, created_at: int = None):
        self._pubkey = pubkey
        self._kind: int = KIND_TEXT_NOTE
        self._content: str = ""
        self._tags: List[List[str]] = []
        self._created_at: int = created_at or int(time.time())

    def metadata(
        self,
        name: str = "",
        about: str = "",
        picture: str = "",
        nip05: str = "",
        banner: str = "",
        website: str = "",
        lud06: str = "",
        lud16: str = "",
    ) -> "EventBuilder":
        """Build a kind-0 metadata event."""
        self._kind = KIND_METADATA
        payload = {}
        if name:     payload["name"] = name
        if about:    payload["about"] = about
        if picture:  payload["picture"] = picture
        if nip05:    payload["nip05"] = nip05
        if banner:   payload["banner"] = banner
        if website:  payload["website"] = website
        if lud06:    payload["lud06"] = lud06
        if lud16:    payload["lud16"] = lud16
        self._content = json.dumps(payload, ensure_ascii=False)
        return self

    def text_note(self, content: str) -> "EventBuilder":
        """Build a kind-1 text note."""
        self._kind = KIND_TEXT_NOTE
        self._content = content
        return self

    def reply_to(
        self,
        event_id: str,
        relay: str = "",
        root_id: str = None,
        root_relay: str = "",
    ) -> "EventBuilder":
        """
        Add NIP-10 reply threading tags.

        If root_id is given, marks the root; event_id is the direct reply target.
        """
        if root_id and root_id != event_id:
            self._tags.append(["e", root_id, root_relay, "root"])
            self._tags.append(["e", event_id, relay, "reply"])
        else:
            self._tags.append(["e", event_id, relay, "reply"])
        return self

    def mention(self, pubkey: str, relay: str = "") -> "EventBuilder":
        """Add a 'p' mention tag."""
        tag = ["p", pubkey]
        if relay:
            tag.append(relay)
        self._tags.append(tag)
        return self

    def add_tag(self, name: str, *values: str) -> "EventBuilder":
        """Add an arbitrary tag."""
        self._tags.append([name, *values])
        return self

    def add_hashtag(self, hashtag: str) -> "EventBuilder":
        """Add a 't' (hashtag) tag. Strips leading '#' if present."""
        tag = hashtag.lstrip("#").lower()
        self._tags.append(["t", tag])
        return self

    def set_expiration(self, timestamp: int) -> "EventBuilder":
        """Add a NIP-40 expiration tag."""
        self._tags.append(["expiration", str(timestamp)])
        return self

    def set_subject(self, subject: str) -> "EventBuilder":
        """Add a subject tag (NIP-14)."""
        self._tags.append(["subject", subject])
        return self

    def set_content_warning(self, reason: str = "") -> "EventBuilder":
        """Add a NIP-36 content-warning tag."""
        tag = ["content-warning"]
        if reason:
            tag.append(reason)
        self._tags.append(tag)
        return self

    def set_nonce(self, nonce: int, target_difficulty: int) -> "EventBuilder":
        """Add a NIP-13 PoW nonce tag."""
        self._tags.append(["nonce", str(nonce), str(target_difficulty)])
        return self

    def article(
        self,
        title: str,
        content: str,
        identifier: str,
        published_at: int = None,
        image: str = "",
        summary: str = "",
        tags: List[str] = None,
    ) -> "EventBuilder":
        """Build a NIP-23 long-form article event (kind 30023)."""
        self._kind = KIND_ARTICLE
        self._content = content
        self._tags.append(["d", identifier])
        self._tags.append(["title", title])
        if published_at:
            self._tags.append(["published_at", str(published_at)])
        if image:
            self._tags.append(["image", image])
        if summary:
            self._tags.append(["summary", summary])
        for t in (tags or []):
            self._tags.append(["t", t.lower()])
        return self

    def reaction(
        self,
        target_event_id: str,
        target_pubkey: str,
        content: str = "+",
    ) -> "EventBuilder":
        """Build a NIP-25 reaction event."""
        self._kind = KIND_REACTION
        self._content = content
        self._tags.append(["e", target_event_id])
        self._tags.append(["p", target_pubkey])
        return self

    def build(self) -> NostrEvent:
        """Finalise and return the NostrEvent."""
        return NostrEvent(
            pubkey=self._pubkey,
            kind=self._kind,
            content=self._content,
            tags=list(self._tags),
            created_at=self._created_at,
        )


# ---------------------------------------------------------------------------
# EventValidator
# ---------------------------------------------------------------------------

class EventValidator:
    """
    Standalone validator for raw event dicts (as received from relays).
    """

    MAX_CONTENT_LENGTH = 65535
    MAX_TIMESTAMP_DRIFT = 120  # seconds

    def validate_id(self, event: dict) -> bool:
        """Recompute and compare the event ID."""
        try:
            serialised = json.dumps(
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
            expected = hashlib.sha256(serialised.encode("utf-8")).hexdigest()
            return event.get("id") == expected
        except (KeyError, TypeError):
            return False

    def validate_timestamp(
        self,
        event: dict,
        max_drift: int = None,
    ) -> bool:
        """Check that created_at is within max_drift seconds of current time."""
        drift = max_drift if max_drift is not None else self.MAX_TIMESTAMP_DRIFT
        created_at = event.get("created_at")
        if not isinstance(created_at, int):
            return False
        now = int(time.time())
        return abs(now - created_at) <= drift

    def validate_content_length(
        self,
        event: dict,
        max_length: int = None,
    ) -> bool:
        """Check content does not exceed maximum length."""
        max_len = max_length if max_length is not None else self.MAX_CONTENT_LENGTH
        content = event.get("content", "")
        return isinstance(content, str) and len(content) <= max_len

    def validate_tags(self, event: dict) -> Tuple[bool, List[str]]:
        """
        Validate all tags in the event.

        Returns
        -------
        (valid: bool, errors: list of str)
        """
        tags = event.get("tags", [])
        errors = []
        if not isinstance(tags, list):
            return False, ["tags must be a list"]

        for i, tag in enumerate(tags):
            if not isinstance(tag, list):
                errors.append(f"tag[{i}] must be a list")
                continue
            if not tag:
                errors.append(f"tag[{i}] is empty")
                continue
            for j, v in enumerate(tag):
                if not isinstance(v, str):
                    errors.append(f"tag[{i}][{j}] must be a string, got {type(v).__name__}")

        return len(errors) == 0, errors

    def validate_kind(self, kind: int) -> bool:
        """Kind must be a non-negative integer (no upper limit in protocol)."""
        return isinstance(kind, int) and kind >= 0

    def validate_pubkey(self, event: dict) -> bool:
        """Pubkey must be a 64-char lowercase hex string."""
        pk = event.get("pubkey", "")
        return bool(isinstance(pk, str) and re.fullmatch(r"[0-9a-f]{64}", pk))

    def full_validate(self, event: dict) -> dict:
        """
        Comprehensive validation report for a raw event dict.

        Returns
        -------
        dict with 'valid' bool and 'checks' dict of individual check results
        """
        id_ok = self.validate_id(event)
        ts_ok = self.validate_timestamp(event)
        content_ok = self.validate_content_length(event)
        tags_ok, tag_errors = self.validate_tags(event)
        kind_ok = self.validate_kind(event.get("kind", -1))
        pubkey_ok = self.validate_pubkey(event)

        has_sig = bool(event.get("sig"))

        all_ok = all([id_ok, content_ok, tags_ok, kind_ok, pubkey_ok])

        return {
            "valid": all_ok,
            "checks": {
                "id_valid": id_ok,
                "timestamp_recent": ts_ok,
                "content_length_ok": content_ok,
                "tags_valid": tags_ok,
                "kind_valid": kind_ok,
                "pubkey_valid": pubkey_ok,
                "has_signature": has_sig,
            },
            "tag_errors": tag_errors,
            "event_id": event.get("id"),
            "kind": event.get("kind"),
            "kind_name": get_kind_name(event.get("kind", -1)),
        }
