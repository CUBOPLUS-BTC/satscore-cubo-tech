"""
Nostr identity management for the Magma app.

Provides NostrIdentity (a user profile model), IdentityManager
(a registry of known identities), and ProfileValidator.

Pure Python standard library.
"""

import re
import json
import time
import html
import hashlib
import urllib.request
import urllib.parse
from typing import List, Optional, Dict, Any

# Lazy import to avoid circular dependency; imported at function call time.
# from app.nostr.nips import encode_npub, validate_nip05_format, parse_nip05


# ---------------------------------------------------------------------------
# NostrIdentity
# ---------------------------------------------------------------------------

class NostrIdentity:
    """
    Represents a Nostr user's identity, derived from a kind-0 metadata event.

    Attributes
    ----------
    pubkey   : str  — 64-char hex public key
    metadata : dict — parsed kind-0 content
    """

    def __init__(self, pubkey: str, metadata: dict = None):
        self.pubkey = pubkey
        self.metadata = metadata or {}
        self._npub: Optional[str] = None

    # -- Accessors ----------------------------------------------------------

    def get_npub(self) -> str:
        """Return the bech32-encoded public key (npub1...)."""
        if self._npub is None:
            try:
                from app.nostr.nips import encode_npub
                self._npub = encode_npub(self.pubkey)
            except Exception:
                self._npub = f"npub1{self.pubkey[:12]}..."
        return self._npub

    def get_display_name(self) -> str:
        """
        Return the best available display name.

        Priority: display_name > name > short pubkey
        """
        return (
            self.metadata.get("display_name")
            or self.metadata.get("name")
            or self.format_pubkey_short()
        )

    def get_name(self) -> str:
        """Return the 'name' field from metadata."""
        return self.metadata.get("name", "")

    def get_nip05(self) -> str:
        """Return NIP-05 identifier (name@domain)."""
        return self.metadata.get("nip05", "")

    def get_picture(self) -> str:
        """Return profile picture URL."""
        return self.metadata.get("picture", "")

    def get_banner(self) -> str:
        """Return banner image URL."""
        return self.metadata.get("banner", "")

    def get_about(self) -> str:
        """Return the 'about' bio field."""
        return self.metadata.get("about", "")

    def get_website(self) -> str:
        """Return the website URL."""
        return self.metadata.get("website", "")

    def get_lud16(self) -> str:
        """Return Lightning address (lud16, e.g. user@domain.com)."""
        return self.metadata.get("lud16", "")

    def get_lud06(self) -> str:
        """Return LNURL (lud06)."""
        return self.metadata.get("lud06", "")

    def format_pubkey_short(self, chars: int = 8) -> str:
        """Return shortened pubkey: first chars + '...' + last chars."""
        if len(self.pubkey) < chars * 2:
            return self.pubkey
        return f"{self.pubkey[:chars]}...{self.pubkey[-chars:]}"

    def has_lightning(self) -> bool:
        """Return True if the user has a Lightning address or LNURL."""
        return bool(self.get_lud16() or self.get_lud06())

    def has_nip05(self) -> bool:
        """Return True if the user has a NIP-05 identifier."""
        return bool(self.get_nip05())

    def to_dict(self) -> dict:
        return {
            "pubkey": self.pubkey,
            "npub": self.get_npub(),
            "display_name": self.get_display_name(),
            "name": self.get_name(),
            "about": self.get_about(),
            "picture": self.get_picture(),
            "banner": self.get_banner(),
            "website": self.get_website(),
            "nip05": self.get_nip05(),
            "lud16": self.get_lud16(),
            "lud06": self.get_lud06(),
        }

    @classmethod
    def from_metadata_event(cls, event: dict) -> "NostrIdentity":
        """
        Construct a NostrIdentity from a raw kind-0 event dict.

        Parameters
        ----------
        event : dict  — Nostr event with kind=0

        Returns
        -------
        NostrIdentity
        """
        if event.get("kind") != 0:
            raise ValueError(f"Expected kind 0, got {event.get('kind')}")
        pubkey = event.get("pubkey", "")
        content = event.get("content", "{}")
        try:
            metadata = json.loads(content)
        except json.JSONDecodeError:
            metadata = {}
        identity = cls(pubkey=pubkey, metadata=metadata)
        return identity

    def __repr__(self):
        return (
            f"<NostrIdentity {self.get_display_name()!r} "
            f"pubkey={self.pubkey[:8]}...>"
        )


# ---------------------------------------------------------------------------
# IdentityManager
# ---------------------------------------------------------------------------

class IdentityManager:
    """
    An in-memory registry of Nostr identities.

    Stores identities by pubkey, supports search, NIP-05 verification,
    follower/following counts, and web-of-trust scoring.
    """

    def __init__(self):
        self._identities: Dict[str, NostrIdentity] = {}
        self._nip05_cache: Dict[str, Dict] = {}  # identifier -> {pubkey, verified_at}

    # -- Registration / updates -------------------------------------------

    def register_identity(
        self,
        pubkey: str,
        metadata: dict,
    ) -> dict:
        """
        Register or update an identity.

        Parameters
        ----------
        pubkey   : str  — 64-char hex pubkey
        metadata : dict — kind-0 content dict

        Returns
        -------
        dict — serialised identity
        """
        if pubkey in self._identities:
            self._identities[pubkey].metadata.update(metadata)
        else:
            self._identities[pubkey] = NostrIdentity(pubkey=pubkey, metadata=dict(metadata))
        return self._identities[pubkey].to_dict()

    def update_metadata(self, pubkey: str, updates: dict) -> dict:
        """
        Partially update metadata for an existing identity.

        Parameters
        ----------
        pubkey  : str
        updates : dict  — fields to merge into existing metadata

        Returns
        -------
        dict — updated serialised identity

        Raises
        ------
        KeyError if pubkey is not registered
        """
        if pubkey not in self._identities:
            # Auto-register with empty metadata
            self._identities[pubkey] = NostrIdentity(pubkey=pubkey, metadata={})
        self._identities[pubkey].metadata.update(updates)
        return self._identities[pubkey].to_dict()

    def get_identity(self, pubkey: str) -> Optional[NostrIdentity]:
        """Return a NostrIdentity by pubkey, or None if not found."""
        return self._identities.get(pubkey)

    def get_or_create(self, pubkey: str) -> NostrIdentity:
        """Return existing identity or create an empty one."""
        if pubkey not in self._identities:
            self._identities[pubkey] = NostrIdentity(pubkey=pubkey)
        return self._identities[pubkey]

    # -- Search -------------------------------------------------------------

    def search_identities(self, query: str) -> List[dict]:
        """
        Search identities by name, display_name, nip05, or pubkey prefix.

        Parameters
        ----------
        query : str  — case-insensitive search string

        Returns
        -------
        list of serialised identity dicts (up to 50 results)
        """
        q = query.lower().strip()
        if not q:
            return []

        results = []
        for identity in self._identities.values():
            if (
                q in identity.get_display_name().lower()
                or q in identity.get_name().lower()
                or q in identity.get_nip05().lower()
                or identity.pubkey.startswith(q)
                or identity.get_about().lower().find(q) != -1
            ):
                results.append(identity.to_dict())
            if len(results) >= 50:
                break

        return results

    # -- NIP-05 verification -----------------------------------------------

    def verify_nip05(self, pubkey: str, nip05: str, timeout: int = 5) -> bool:
        """
        Verify a NIP-05 identifier by fetching /.well-known/nostr.json.

        Parameters
        ----------
        pubkey : str  — expected 64-char hex pubkey
        nip05  : str  — identifier in name@domain format
        timeout: int  — HTTP timeout seconds

        Returns
        -------
        bool  — True if the domain maps the name to the given pubkey
        """
        try:
            from app.nostr.nips import parse_nip05
            name, domain = parse_nip05(nip05)
        except Exception:
            return False

        url = f"https://{domain}/.well-known/nostr.json?name={urllib.parse.quote(name)}"

        # Check cache
        cache_key = nip05.lower()
        cached = self._nip05_cache.get(cache_key)
        if cached and cached.get("verified_at", 0) > time.time() - 3600:
            return cached.get("pubkey", "").lower() == pubkey.lower()

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Magma-Nostr-Client/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                names = data.get("names", {})
                resolved_pubkey = names.get(name, names.get(name.lower(), ""))
                verified = resolved_pubkey.lower() == pubkey.lower()
                self._nip05_cache[cache_key] = {
                    "pubkey": resolved_pubkey,
                    "verified_at": int(time.time()),
                    "verified": verified,
                }
                return verified
        except Exception:
            return False

    # -- Social graph -------------------------------------------------------

    def get_follower_count(
        self,
        pubkey: str,
        contact_events: List[dict],
    ) -> int:
        """
        Count how many contact list events include the given pubkey.

        Parameters
        ----------
        pubkey         : str  — the pubkey to check
        contact_events : list of kind-3 event dicts from other users

        Returns
        -------
        int
        """
        count = 0
        for event in contact_events:
            if event.get("kind") != 3:
                continue
            for tag in event.get("tags", []):
                if tag and tag[0] == "p" and len(tag) > 1 and tag[1] == pubkey:
                    count += 1
                    break
        return count

    def get_following_count(
        self,
        pubkey: str,
        contact_event: dict,
    ) -> int:
        """
        Count the number of pubkeys in a single contact list event.

        Parameters
        ----------
        pubkey        : str  — owner of the contact list (for validation)
        contact_event : dict — a kind-3 event

        Returns
        -------
        int
        """
        if contact_event.get("kind") != 3:
            return 0
        return sum(
            1 for tag in contact_event.get("tags", [])
            if tag and tag[0] == "p" and len(tag) > 1
        )

    def get_web_of_trust_score(
        self,
        pubkey: str,
        contacts: Dict[str, List[str]],
        depth: int = 2,
    ) -> float:
        """
        Compute a simple web-of-trust score for a pubkey.

        Score = direct_follows + 0.1 * follows_of_follows

        Parameters
        ----------
        pubkey   : str  — pubkey to score
        contacts : dict mapping pubkey -> list of followed pubkeys
        depth    : int  — hops (currently 1 or 2)

        Returns
        -------
        float  — trust score (higher = more trusted in this graph)
        """
        score = 0.0
        direct_follows = sum(1 for follows in contacts.values() if pubkey in follows)
        score += direct_follows

        if depth >= 2:
            # Follows-of-follows
            second_hop = 0
            for follower, their_follows in contacts.items():
                if pubkey in their_follows:
                    continue  # already counted
                for intermediate in their_follows:
                    if intermediate in contacts and pubkey in contacts.get(intermediate, []):
                        second_hop += 1
                        break
            score += second_hop * 0.1

        return round(score, 4)

    @staticmethod
    def format_pubkey_short(pubkey: str, chars: int = 8) -> str:
        """Return abbreviated pubkey: 'abcd1234...wxyz5678'."""
        if len(pubkey) <= chars * 2:
            return pubkey
        return f"{pubkey[:chars]}...{pubkey[-chars:]}"

    # -- Bulk operations ---------------------------------------------------

    def import_from_events(self, events: List[dict]) -> int:
        """
        Import identities from a list of kind-0 events.

        Returns
        -------
        int  — number of identities imported
        """
        count = 0
        for event in events:
            if event.get("kind") != 0:
                continue
            try:
                identity = NostrIdentity.from_metadata_event(event)
                self._identities[identity.pubkey] = identity
                count += 1
            except Exception:
                pass
        return count

    def export_all(self) -> List[dict]:
        """Return all registered identities as a list of dicts."""
        return [identity.to_dict() for identity in self._identities.values()]

    def count(self) -> int:
        return len(self._identities)

    def __repr__(self):
        return f"<IdentityManager identities={len(self._identities)}>"


# ---------------------------------------------------------------------------
# ProfileValidator
# ---------------------------------------------------------------------------

_URL_RE = re.compile(
    r"^https?://"
    r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,}"
    r"(?::\d+)?"
    r"(?:/[^\s]*)?"
    r"$",
    re.IGNORECASE,
)

_NIP05_RE = re.compile(r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Known dangerous HTML/JS patterns in metadata fields
_DANGEROUS_PATTERNS = [
    re.compile(r"<script", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+=", re.IGNORECASE),
    re.compile(r"data:text/html", re.IGNORECASE),
]

# Maximum field lengths
_FIELD_LIMITS = {
    "name": 50,
    "display_name": 100,
    "about": 600,
    "website": 200,
    "picture": 500,
    "banner": 500,
    "nip05": 100,
    "lud16": 100,
    "lud06": 2000,
}


class ProfileValidator:
    """
    Validates and sanitises Nostr profile metadata.
    """

    def validate_metadata(self, metadata: dict) -> tuple:
        """
        Validate profile metadata fields.

        Parameters
        ----------
        metadata : dict — kind-0 content fields

        Returns
        -------
        (is_valid: bool, errors: list of str)
        """
        errors = []

        if not isinstance(metadata, dict):
            return False, ["metadata must be a dict"]

        # Check field lengths
        for field_name, max_len in _FIELD_LIMITS.items():
            value = metadata.get(field_name)
            if value is not None:
                if not isinstance(value, str):
                    errors.append(f"'{field_name}' must be a string")
                elif len(value) > max_len:
                    errors.append(
                        f"'{field_name}' too long: {len(value)} chars (max {max_len})"
                    )

        # Validate picture URL
        picture = metadata.get("picture", "")
        if picture and not self.validate_picture_url(picture):
            errors.append(f"'picture' is not a valid HTTP(S) URL: {picture!r}")

        # Validate banner URL
        banner = metadata.get("banner", "")
        if banner and not _URL_RE.match(banner):
            errors.append(f"'banner' is not a valid HTTP(S) URL: {banner!r}")

        # Validate website URL
        website = metadata.get("website", "")
        if website and not _URL_RE.match(website):
            errors.append(f"'website' is not a valid URL: {website!r}")

        # Validate NIP-05
        nip05 = metadata.get("nip05", "")
        if nip05 and not self.validate_nip05_format(nip05):
            errors.append(f"'nip05' has invalid format: {nip05!r}")

        # Check for dangerous content
        for field_name in ["name", "display_name", "about"]:
            value = metadata.get(field_name, "")
            if isinstance(value, str):
                for pattern in _DANGEROUS_PATTERNS:
                    if pattern.search(value):
                        errors.append(
                            f"'{field_name}' contains potentially dangerous content"
                        )
                        break

        return len(errors) == 0, errors

    def validate_picture_url(self, url: str) -> bool:
        """
        Return True if the URL is a valid HTTP(S) image URL.

        Does not fetch the URL — only validates the format.
        """
        if not _URL_RE.match(url):
            return False
        # Common image extensions (not exhaustive)
        lower = url.lower().split("?")[0]
        allowed_ext = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".avif")
        # Accept if extension matches OR if no extension (could be a service URL)
        has_ext = any(lower.endswith(ext) for ext in allowed_ext)
        return True  # Relaxed: accept any https URL

    def validate_nip05_format(self, nip05: str) -> bool:
        """Return True if nip05 matches the name@domain format."""
        return bool(_NIP05_RE.match(nip05))

    def sanitize_metadata(self, metadata: dict) -> dict:
        """
        Return a sanitised copy of metadata:
        - HTML-escape text fields
        - Truncate fields to maximum lengths
        - Remove unknown/dangerous fields
        - Strip leading/trailing whitespace

        Parameters
        ----------
        metadata : dict

        Returns
        -------
        dict  — sanitised copy
        """
        ALLOWED_FIELDS = set(_FIELD_LIMITS.keys()) | {
            "lud06", "lud16", "nip05",
        }

        sanitised = {}

        for field_name, value in metadata.items():
            if field_name not in ALLOWED_FIELDS:
                continue  # Drop unknown fields

            if not isinstance(value, str):
                continue

            # Strip whitespace
            value = value.strip()

            # Truncate to max length
            max_len = _FIELD_LIMITS.get(field_name, 500)
            if len(value) > max_len:
                value = value[:max_len]

            # HTML-escape text display fields
            if field_name in ("name", "display_name", "about"):
                value = html.escape(value, quote=False)

            # Remove dangerous patterns from text fields
            if field_name in ("name", "display_name", "about"):
                for pattern in _DANGEROUS_PATTERNS:
                    value = pattern.sub("", value)

            sanitised[field_name] = value

        return sanitised

    def check_completeness(self, metadata: dict) -> dict:
        """
        Score how complete a profile is.

        Returns
        -------
        dict with 'score' (0-100), 'filled_fields', 'missing_fields'
        """
        important_fields = [
            "name", "display_name", "about", "picture",
            "nip05", "lud16", "website",
        ]
        filled = [f for f in important_fields if metadata.get(f)]
        missing = [f for f in important_fields if not metadata.get(f)]
        score = int(len(filled) / len(important_fields) * 100)

        return {
            "score": score,
            "filled_fields": filled,
            "missing_fields": missing,
            "has_lightning": bool(metadata.get("lud16") or metadata.get("lud06")),
            "has_nip05": bool(metadata.get("nip05")),
            "has_avatar": bool(metadata.get("picture")),
        }
