"""
Nostr subscription filters (NIP-01, NIP-50).

Provides the Filter and FilterBuilder classes for constructing
REQ subscription filters, and SubscriptionManager for tracking
active subscriptions.

Pure Python standard library.
"""

import json
import time
import uuid
from typing import List, Optional, Dict, Any, Tuple


class Filter:
    """
    Represents a single Nostr subscription filter per NIP-01.

    A filter can specify:
        ids      - list of event IDs (or prefixes)
        authors  - list of pubkeys (or prefixes)
        kinds    - list of event kinds
        since    - only events after this Unix timestamp
        until    - only events before this Unix timestamp
        limit    - maximum number of events to return
        #e       - list of referenced event IDs
        #p       - list of referenced pubkeys
        #t       - list of hashtags
        #d       - list of 'd' tag values
        search   - full-text search string (NIP-50)
    """

    def __init__(
        self,
        ids: List[str] = None,
        authors: List[str] = None,
        kinds: List[int] = None,
        since: int = None,
        until: int = None,
        limit: int = None,
        tags: Dict[str, List[str]] = None,
        search: str = None,
    ):
        self.ids: Optional[List[str]] = ids
        self.authors: Optional[List[str]] = authors
        self.kinds: Optional[List[int]] = kinds
        self.since: Optional[int] = since
        self.until: Optional[int] = until
        self.limit: Optional[int] = limit
        self.tags: Dict[str, List[str]] = tags or {}  # {'e': [...], 'p': [...]}
        self.search: Optional[str] = search

    # -- Event matching -----------------------------------------------------

    def matches(self, event: dict) -> bool:
        """
        Check if an event matches this filter.

        Parameters
        ----------
        event : dict  — a Nostr event dict

        Returns
        -------
        bool
        """
        # IDs filter (prefix matching supported)
        if self.ids is not None:
            event_id = event.get("id", "")
            if not any(event_id.startswith(prefix) for prefix in self.ids):
                return False

        # Authors filter (prefix matching supported)
        if self.authors is not None:
            pubkey = event.get("pubkey", "")
            if not any(pubkey.startswith(prefix) for prefix in self.authors):
                return False

        # Kinds filter
        if self.kinds is not None:
            if event.get("kind") not in self.kinds:
                return False

        # Timestamp filters
        created_at = event.get("created_at", 0)
        if self.since is not None and created_at < self.since:
            return False
        if self.until is not None and created_at > self.until:
            return False

        # Tag filters
        for tag_name, required_values in self.tags.items():
            event_tag_values = [
                tag[1]
                for tag in event.get("tags", [])
                if tag and len(tag) >= 2 and tag[0] == tag_name
            ]
            # At least one of the required values must appear in event tags
            if not any(v in event_tag_values for v in required_values):
                return False

        # Full-text search (simple substring match — relay-side NIP-50 does more)
        if self.search is not None:
            content = event.get("content", "").lower()
            if self.search.lower() not in content:
                return False

        return True

    # -- Serialisation ------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise to a dict suitable for a REQ message."""
        d: dict = {}
        if self.ids is not None:
            d["ids"] = self.ids
        if self.authors is not None:
            d["authors"] = self.authors
        if self.kinds is not None:
            d["kinds"] = self.kinds
        if self.since is not None:
            d["since"] = self.since
        if self.until is not None:
            d["until"] = self.until
        if self.limit is not None:
            d["limit"] = self.limit
        if self.search is not None:
            d["search"] = self.search
        for tag_name, values in self.tags.items():
            d[f"#{tag_name}"] = values
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Filter":
        """Deserialise from a dict (as parsed from a REQ message)."""
        tags: Dict[str, List[str]] = {}
        for key, value in data.items():
            if key.startswith("#") and len(key) == 2:
                tag_name = key[1:]
                tags[tag_name] = value

        return cls(
            ids=data.get("ids"),
            authors=data.get("authors"),
            kinds=data.get("kinds"),
            since=data.get("since"),
            until=data.get("until"),
            limit=data.get("limit"),
            tags=tags,
            search=data.get("search"),
        )

    # -- Utilities ----------------------------------------------------------

    def is_empty(self) -> bool:
        """Return True if the filter has no constraints at all."""
        return all([
            self.ids is None,
            self.authors is None,
            self.kinds is None,
            self.since is None,
            self.until is None,
            self.limit is None,
            not self.tags,
            self.search is None,
        ])

    def merge(self, other: "Filter") -> "Filter":
        """
        Merge two filters by taking the union of list fields and the
        most permissive timestamp constraints.

        Note: merging filters is only meaningful when both use the same
        field for the same logical purpose.
        """
        def merge_lists(a, b):
            if a is None and b is None:
                return None
            combined = list(set((a or []) + (b or [])))
            return combined if combined else None

        merged_tags: Dict[str, List[str]] = {}
        for k, v in self.tags.items():
            merged_tags[k] = list(set(v + other.tags.get(k, [])))
        for k, v in other.tags.items():
            if k not in merged_tags:
                merged_tags[k] = v

        return Filter(
            ids=merge_lists(self.ids, other.ids),
            authors=merge_lists(self.authors, other.authors),
            kinds=merge_lists(self.kinds, other.kinds),
            since=min(s for s in [self.since, other.since] if s is not None) if any(
                s is not None for s in [self.since, other.since]
            ) else None,
            until=max(u for u in [self.until, other.until] if u is not None) if any(
                u is not None for u in [self.until, other.until]
            ) else None,
            limit=max(l for l in [self.limit, other.limit] if l is not None) if any(
                l is not None for l in [self.limit, other.limit]
            ) else None,
            tags=merged_tags,
            search=self.search or other.search,
        )

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate filter fields.

        Returns
        -------
        (is_valid: bool, errors: list of str)
        """
        errors = []

        if self.ids is not None:
            for idx, id_prefix in enumerate(self.ids):
                if not isinstance(id_prefix, str):
                    errors.append(f"ids[{idx}] must be a string")
                elif not all(c in "0123456789abcdef" for c in id_prefix.lower()):
                    errors.append(f"ids[{idx}] must be a hex string, got {id_prefix!r}")
                elif len(id_prefix) > 64:
                    errors.append(f"ids[{idx}] too long (max 64 chars)")

        if self.authors is not None:
            for idx, author in enumerate(self.authors):
                if not isinstance(author, str):
                    errors.append(f"authors[{idx}] must be a string")
                elif len(author) > 64:
                    errors.append(f"authors[{idx}] too long (max 64 chars)")

        if self.kinds is not None:
            for idx, kind in enumerate(self.kinds):
                if not isinstance(kind, int) or kind < 0:
                    errors.append(f"kinds[{idx}] must be a non-negative integer")

        if self.since is not None and not isinstance(self.since, int):
            errors.append("since must be an integer")
        if self.until is not None and not isinstance(self.until, int):
            errors.append("until must be an integer")
        if (
            self.since is not None
            and self.until is not None
            and self.since > self.until
        ):
            errors.append(f"since ({self.since}) must be <= until ({self.until})")

        if self.limit is not None:
            if not isinstance(self.limit, int) or self.limit < 0:
                errors.append("limit must be a non-negative integer")

        return len(errors) == 0, errors

    def __repr__(self):
        parts = []
        if self.kinds:
            parts.append(f"kinds={self.kinds}")
        if self.authors:
            parts.append(f"authors=[{len(self.authors)} pubkeys]")
        if self.since or self.until:
            parts.append(f"time_range=[{self.since},{self.until}]")
        return f"<Filter {' '.join(parts) or 'empty'}>"


# ---------------------------------------------------------------------------
# FilterBuilder
# ---------------------------------------------------------------------------

class FilterBuilder:
    """
    Fluent builder for constructing Filter objects.

    Usage
    -----
    f = (
        FilterBuilder()
        .kinds(1, 6)
        .authors("deadbeef...")
        .since(int(time.time()) - 3600)
        .limit(50)
        .build()
    )
    """

    def __init__(self):
        self._ids: Optional[List[str]] = None
        self._authors: Optional[List[str]] = None
        self._kinds: Optional[List[int]] = None
        self._since: Optional[int] = None
        self._until: Optional[int] = None
        self._limit: Optional[int] = None
        self._tags: Dict[str, List[str]] = {}
        self._search: Optional[str] = None

    def ids(self, *event_ids: str) -> "FilterBuilder":
        """Filter by event IDs (or hex prefixes)."""
        self._ids = list(event_ids)
        return self

    def authors(self, *pubkeys: str) -> "FilterBuilder":
        """Filter by author pubkeys (or hex prefixes)."""
        self._authors = list(pubkeys)
        return self

    def kinds(self, *kinds: int) -> "FilterBuilder":
        """Filter by event kinds."""
        self._kinds = list(kinds)
        return self

    def since(self, timestamp: int) -> "FilterBuilder":
        """Only events after this Unix timestamp (inclusive)."""
        self._since = timestamp
        return self

    def until(self, timestamp: int) -> "FilterBuilder":
        """Only events before this Unix timestamp (inclusive)."""
        self._until = timestamp
        return self

    def limit(self, n: int) -> "FilterBuilder":
        """Maximum number of events to return."""
        self._limit = n
        return self

    def references_events(self, *event_ids: str) -> "FilterBuilder":
        """Filter by referenced 'e' tags."""
        self._tags["e"] = list(event_ids)
        return self

    def references_pubkeys(self, *pubkeys: str) -> "FilterBuilder":
        """Filter by referenced 'p' tags."""
        self._tags["p"] = list(pubkeys)
        return self

    def hashtags(self, *tags: str) -> "FilterBuilder":
        """Filter by 't' (hashtag) tags. Strips leading '#' automatically."""
        self._tags["t"] = [t.lstrip("#").lower() for t in tags]
        return self

    def identifiers(self, *identifiers: str) -> "FilterBuilder":
        """Filter by 'd' tag values (for parameterized replaceable events)."""
        self._tags["d"] = list(identifiers)
        return self

    def tag(self, tag_name: str, *values: str) -> "FilterBuilder":
        """Add a generic tag filter."""
        self._tags[tag_name] = list(values)
        return self

    def search(self, query: str) -> "FilterBuilder":
        """Full-text search string (NIP-50)."""
        self._search = query
        return self

    def last_n_hours(self, hours: float) -> "FilterBuilder":
        """Convenience: set since to now - hours."""
        self._since = int(time.time() - hours * 3600)
        return self

    def last_n_days(self, days: int) -> "FilterBuilder":
        """Convenience: set since to now - days."""
        self._since = int(time.time() - days * 86400)
        return self

    def build(self) -> Filter:
        """Construct and return the Filter."""
        return Filter(
            ids=self._ids,
            authors=self._authors,
            kinds=self._kinds,
            since=self._since,
            until=self._until,
            limit=self._limit,
            tags=dict(self._tags),
            search=self._search,
        )


# ---------------------------------------------------------------------------
# SubscriptionManager
# ---------------------------------------------------------------------------

class SubscriptionManager:
    """
    Tracks active Nostr subscriptions and builds REQ/CLOSE messages.

    Each subscription is identified by a unique subscription ID and
    associated with a list of Filter objects.
    """

    def __init__(self, prefix: str = "sub"):
        self._subscriptions: Dict[str, Dict[str, Any]] = {}
        self._prefix = prefix
        self._counter = 0

    # -- Subscription lifecycle -------------------------------------------

    def create_subscription(
        self,
        filters: List[Filter],
        sub_id: str = None,
    ) -> str:
        """
        Register a new subscription.

        Parameters
        ----------
        filters : list of Filter objects
        sub_id  : optional custom subscription ID

        Returns
        -------
        str — subscription ID
        """
        if sub_id is None:
            self._counter += 1
            sub_id = f"{self._prefix}-{self._counter}-{uuid.uuid4().hex[:8]}"

        self._subscriptions[sub_id] = {
            "id": sub_id,
            "filters": filters,
            "created_at": int(time.time()),
            "event_count": 0,
            "eose_received": False,
        }
        return sub_id

    def close_subscription(self, sub_id: str):
        """Remove a subscription by ID."""
        self._subscriptions.pop(sub_id, None)

    def get_active_subscriptions(self) -> List[dict]:
        """
        Return all active subscriptions as a list of info dicts.
        """
        result = []
        for sub_id, sub in self._subscriptions.items():
            result.append({
                "id": sub_id,
                "filter_count": len(sub["filters"]),
                "created_at": sub["created_at"],
                "event_count": sub["event_count"],
                "eose_received": sub["eose_received"],
                "filters": [f.to_dict() for f in sub["filters"]],
            })
        return result

    def get_subscription(self, sub_id: str) -> Optional[dict]:
        """Return info for a specific subscription."""
        return self._subscriptions.get(sub_id)

    def record_event(self, sub_id: str):
        """Increment the event counter for a subscription."""
        if sub_id in self._subscriptions:
            self._subscriptions[sub_id]["event_count"] += 1

    def record_eose(self, sub_id: str):
        """Mark EOSE (End of Stored Events) received for a subscription."""
        if sub_id in self._subscriptions:
            self._subscriptions[sub_id]["eose_received"] = True

    def matches_any(self, sub_id: str, event: dict) -> bool:
        """
        Check if an event matches any filter in a subscription.
        """
        sub = self._subscriptions.get(sub_id)
        if not sub:
            return False
        return any(f.matches(event) for f in sub["filters"])

    # -- Message builders ---------------------------------------------------

    def build_req_message(self, sub_id: str, filters: List[Filter]) -> str:
        """
        Build a JSON REQ message string.

        Format: ["REQ", subscription_id, filter1, filter2, ...]
        """
        parts = ["REQ", sub_id] + [f.to_dict() for f in filters]
        return json.dumps(parts, separators=(",", ":"))

    def build_close_message(self, sub_id: str) -> str:
        """
        Build a JSON CLOSE message string.

        Format: ["CLOSE", subscription_id]
        """
        return json.dumps(["CLOSE", sub_id], separators=(",", ":"))

    def build_event_message(self, sub_id: str, event: dict) -> str:
        """
        Build a JSON EVENT message string.

        Format: ["EVENT", subscription_id, event]
        """
        return json.dumps(["EVENT", sub_id, event], separators=(",", ":"))

    # -- Utilities ----------------------------------------------------------

    @property
    def count(self) -> int:
        """Number of active subscriptions."""
        return len(self._subscriptions)

    def clear(self):
        """Remove all subscriptions."""
        self._subscriptions.clear()

    def __repr__(self):
        return f"<SubscriptionManager active={self.count}>"
