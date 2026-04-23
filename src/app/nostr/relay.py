"""
Nostr relay communication helpers.

Provides RelayInfo (NIP-11 info documents), RelayMessage (message
parsing/building), RelayConnection (per-relay state), and RelayPool
(multi-relay management).

All I/O is abstracted — this module does not itself open sockets.
Actual WebSocket transport is handled by the HTTP server layer.

Pure Python standard library.
"""

import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

# ---------------------------------------------------------------------------
# Well-known relay URLs
# ---------------------------------------------------------------------------

DEFAULT_RELAYS: List[str] = [
    "wss://relay.damus.io",
    "wss://relay.nostr.band",
    "wss://nos.lol",
    "wss://relay.snort.social",
    "wss://purplepag.es",
    "wss://nostr.wine",
    "wss://relay.primal.net",
    "wss://eden.nostr.land",
    "wss://nostr-pub.wellorder.net",
    "wss://relay.current.fyi",
    "wss://nostr.bitcoiner.social",
    "wss://relay.orangepill.dev",
    "wss://nostr.zbd.gg",
    "wss://relay.nostr.wirednet.jp",
    "wss://relay.nostr.bg",
    "wss://nostr.oxtr.dev",
]


# ---------------------------------------------------------------------------
# RelayInfo (NIP-11)
# ---------------------------------------------------------------------------

@dataclass
class RelayInfo:
    """
    NIP-11 relay information document.

    Served by relays at their WebSocket URL with an HTTP GET
    and Accept: application/nostr+json header.
    """
    name: str = ""
    description: str = ""
    pubkey: str = ""
    contact: str = ""
    supported_nips: List[int] = field(default_factory=list)
    software: str = ""
    version: str = ""
    # Relay limitations
    limitation: Dict[str, Any] = field(default_factory=dict)
    # Optional fields
    icon: str = ""
    banner: str = ""
    payments_url: str = ""
    fees: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "RelayInfo":
        """Parse from a NIP-11 JSON dict."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            pubkey=data.get("pubkey", ""),
            contact=data.get("contact", ""),
            supported_nips=data.get("supported_nips", []),
            software=data.get("software", ""),
            version=data.get("version", ""),
            limitation=data.get("limitation", {}),
            icon=data.get("icon", ""),
            banner=data.get("banner", ""),
            payments_url=data.get("payments_url", ""),
            fees=data.get("fees", {}),
        )

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "description": self.description,
            "pubkey": self.pubkey,
            "contact": self.contact,
            "supported_nips": self.supported_nips,
            "software": self.software,
            "version": self.version,
        }
        if self.limitation:
            d["limitation"] = self.limitation
        if self.icon:
            d["icon"] = self.icon
        if self.banner:
            d["banner"] = self.banner
        if self.payments_url:
            d["payments_url"] = self.payments_url
        if self.fees:
            d["fees"] = self.fees
        return d

    def supports_nip(self, nip: int) -> bool:
        """Return True if this relay advertises support for the given NIP number."""
        return nip in self.supported_nips

    def get_max_message_length(self) -> Optional[int]:
        return self.limitation.get("max_message_length")

    def get_max_subscriptions(self) -> Optional[int]:
        return self.limitation.get("max_subscriptions")

    def get_max_filters(self) -> Optional[int]:
        return self.limitation.get("max_filters")

    def requires_auth(self) -> bool:
        return bool(self.limitation.get("auth_required", False))

    def requires_payment(self) -> bool:
        return bool(self.limitation.get("payment_required", False))

    def __repr__(self):
        return f"<RelayInfo name={self.name!r} nips={self.supported_nips}>"


# ---------------------------------------------------------------------------
# RelayMessage
# ---------------------------------------------------------------------------

class RelayMessage:
    """
    Parse and build Nostr relay protocol messages.

    Nostr relay message types:
        Client -> Relay: EVENT, REQ, CLOSE, AUTH
        Relay -> Client: EVENT, OK, EOSE, NOTICE, AUTH, COUNT
    """

    @staticmethod
    def parse(raw: str) -> dict:
        """
        Parse a raw JSON message string from a relay.

        Returns
        -------
        dict with 'type' and relevant fields:
            EVENT  -> {type, subscription_id, event}
            OK     -> {type, event_id, accepted, message}
            EOSE   -> {type, subscription_id}
            NOTICE -> {type, message}
            AUTH   -> {type, challenge}
            COUNT  -> {type, subscription_id, count}
            CLOSED -> {type, subscription_id, message}
        """
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError as e:
            return {"type": "ERROR", "error": f"JSON parse error: {e}", "raw": raw}

        if not isinstance(msg, list) or not msg:
            return {"type": "ERROR", "error": "Expected a non-empty JSON array", "raw": raw}

        msg_type = msg[0]

        if msg_type == "EVENT":
            if len(msg) < 3:
                return {"type": "ERROR", "error": "EVENT message too short"}
            return {
                "type": "EVENT",
                "subscription_id": msg[1],
                "event": msg[2],
            }

        if msg_type == "OK":
            if len(msg) < 3:
                return {"type": "ERROR", "error": "OK message too short"}
            return {
                "type": "OK",
                "event_id": msg[1],
                "accepted": bool(msg[2]),
                "message": msg[3] if len(msg) > 3 else "",
            }

        if msg_type == "EOSE":
            if len(msg) < 2:
                return {"type": "ERROR", "error": "EOSE message too short"}
            return {
                "type": "EOSE",
                "subscription_id": msg[1],
            }

        if msg_type == "NOTICE":
            return {
                "type": "NOTICE",
                "message": msg[1] if len(msg) > 1 else "",
            }

        if msg_type == "AUTH":
            return {
                "type": "AUTH",
                "challenge": msg[1] if len(msg) > 1 else "",
            }

        if msg_type == "COUNT":
            if len(msg) < 3:
                return {"type": "ERROR", "error": "COUNT message too short"}
            return {
                "type": "COUNT",
                "subscription_id": msg[1],
                "count": msg[2].get("count") if isinstance(msg[2], dict) else msg[2],
            }

        if msg_type == "CLOSED":
            return {
                "type": "CLOSED",
                "subscription_id": msg[1] if len(msg) > 1 else "",
                "message": msg[2] if len(msg) > 2 else "",
            }

        return {"type": "UNKNOWN", "raw_type": msg_type, "data": msg}

    @staticmethod
    def build_event(event: dict) -> str:
        """Build a CLIENT->RELAY EVENT message: ["EVENT", event]"""
        return json.dumps(["EVENT", event], separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def build_req(sub_id: str, *filters) -> str:
        """Build a REQ message: ["REQ", sub_id, filter1, ...]"""
        parts = ["REQ", sub_id]
        for f in filters:
            if hasattr(f, "to_dict"):
                parts.append(f.to_dict())
            else:
                parts.append(f)
        return json.dumps(parts, separators=(",", ":"))

    @staticmethod
    def build_close(sub_id: str) -> str:
        """Build a CLOSE message: ["CLOSE", sub_id]"""
        return json.dumps(["CLOSE", sub_id], separators=(",", ":"))

    @staticmethod
    def build_auth(event: dict) -> str:
        """Build an AUTH message: ["AUTH", event]"""
        return json.dumps(["AUTH", event], separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def build_count(sub_id: str, *filters) -> str:
        """Build a COUNT message (NIP-45): ["COUNT", sub_id, filter1, ...]"""
        parts = ["COUNT", sub_id]
        for f in filters:
            if hasattr(f, "to_dict"):
                parts.append(f.to_dict())
            else:
                parts.append(f)
        return json.dumps(parts, separators=(",", ":"))


# ---------------------------------------------------------------------------
# RelayConnection
# ---------------------------------------------------------------------------

class RelayConnection:
    """
    Represents the configuration and state of a connection to a single relay.

    This class does not manage an actual WebSocket connection — it stores
    state, queues outbound messages, and tracks statistics. Actual transport
    is handled by the application's async/threading layer.
    """

    def __init__(self, url: str, read: bool = True, write: bool = True):
        self.url = url
        self.read = read
        self.write = write
        self._info: Optional[RelayInfo] = None
        self._connected = False
        self._outbound_queue: List[str] = []
        self._stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "events_received": 0,
            "errors": 0,
            "connect_time": None,
            "last_message_at": None,
            "latency_ms": None,
        }

    # -- NIP-11 info --------------------------------------------------------

    def get_info(self, timeout: int = 5) -> Optional[RelayInfo]:
        """
        Fetch the NIP-11 relay info document via HTTP GET.

        Converts wss:// -> https:// for the HTTP request.
        Returns None if unavailable.
        """
        http_url = self.url.replace("wss://", "https://").replace("ws://", "http://")
        try:
            req = urllib.request.Request(
                http_url,
                headers={"Accept": "application/nostr+json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self._info = RelayInfo.from_dict(data)
                return self._info
        except Exception:
            return None

    @property
    def info(self) -> Optional[RelayInfo]:
        """Cached relay info (call get_info() first)."""
        return self._info

    # -- Connection state ---------------------------------------------------

    def mark_connected(self):
        self._connected = True
        self._stats["connect_time"] = int(time.time())

    def mark_disconnected(self):
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_url(self) -> str:
        return self.url

    def get_supported_nips(self) -> List[int]:
        if self._info:
            return self._info.supported_nips
        return []

    # -- Messaging ----------------------------------------------------------

    def send_message(self, msg: str):
        """Queue a message for sending."""
        self._outbound_queue.append(msg)
        self._stats["messages_sent"] += 1

    def pop_outbound(self) -> Optional[str]:
        """Dequeue the next outbound message."""
        if self._outbound_queue:
            return self._outbound_queue.pop(0)
        return None

    def flush_outbound(self) -> List[str]:
        """Return and clear all queued outbound messages."""
        msgs = list(self._outbound_queue)
        self._outbound_queue.clear()
        return msgs

    def record_received(self, msg_type: str = "EVENT"):
        self._stats["messages_received"] += 1
        self._stats["last_message_at"] = int(time.time())
        if msg_type == "EVENT":
            self._stats["events_received"] += 1

    def record_error(self):
        self._stats["errors"] += 1

    # -- Stats --------------------------------------------------------------

    def get_stats(self) -> dict:
        """Return connection statistics."""
        return {
            "url": self.url,
            "connected": self._connected,
            "read": self.read,
            "write": self.write,
            "queue_depth": len(self._outbound_queue),
            **self._stats,
        }

    def __repr__(self):
        state = "connected" if self._connected else "disconnected"
        return f"<RelayConnection url={self.url!r} {state} r={self.read} w={self.write}>"


# ---------------------------------------------------------------------------
# RelayPool
# ---------------------------------------------------------------------------

class RelayPool:
    """
    Manages a pool of relay connections for reading and writing events.

    Supports adding/removing relays, querying across read relays,
    publishing to write relays, and per-relay statistics.
    """

    def __init__(self):
        self._relays: Dict[str, RelayConnection] = {}

    # -- Management ---------------------------------------------------------

    def add_relay(self, url: str, read: bool = True, write: bool = True):
        """Add a relay to the pool."""
        if url in self._relays:
            # Update permissions
            self._relays[url].read = read
            self._relays[url].write = write
        else:
            self._relays[url] = RelayConnection(url, read=read, write=write)

    def remove_relay(self, url: str):
        """Remove a relay from the pool."""
        self._relays.pop(url, None)

    def get_relays(self) -> List[RelayConnection]:
        """Return all relay connections."""
        return list(self._relays.values())

    def get_read_relays(self) -> List[RelayConnection]:
        """Return connections designated for reading."""
        return [r for r in self._relays.values() if r.read]

    def get_write_relays(self) -> List[RelayConnection]:
        """Return connections designated for writing."""
        return [r for r in self._relays.values() if r.write]

    def get_relay(self, url: str) -> Optional[RelayConnection]:
        return self._relays.get(url)

    # -- Publishing ---------------------------------------------------------

    def publish(self, event: dict) -> Dict[str, Any]:
        """
        Queue an EVENT message for all write relays.

        Returns
        -------
        dict mapping relay_url -> {'queued': bool}
        """
        msg = RelayMessage.build_event(event)
        result = {}
        for relay in self.get_write_relays():
            try:
                relay.send_message(msg)
                result[relay.url] = {"queued": True}
            except Exception as e:
                result[relay.url] = {"queued": False, "error": str(e)}
        return result

    def query(self, filters: list, sub_id: str = None) -> Dict[str, Any]:
        """
        Queue REQ messages for all read relays.

        Parameters
        ----------
        filters : list of Filter objects or dicts
        sub_id  : optional subscription ID

        Returns
        -------
        dict mapping relay_url -> {'queued': bool}
        """
        import uuid as _uuid
        if sub_id is None:
            sub_id = f"pool-{_uuid.uuid4().hex[:12]}"

        msg = RelayMessage.build_req(sub_id, *filters)
        result = {}
        for relay in self.get_read_relays():
            try:
                relay.send_message(msg)
                result[relay.url] = {"queued": True, "sub_id": sub_id}
            except Exception as e:
                result[relay.url] = {"queued": False, "error": str(e)}

        return result

    def close_subscription(self, sub_id: str) -> Dict[str, bool]:
        """Send a CLOSE message to all read relays."""
        msg = RelayMessage.build_close(sub_id)
        result = {}
        for relay in self.get_read_relays():
            relay.send_message(msg)
            result[relay.url] = True
        return result

    # -- Pool introspection -------------------------------------------------

    def get_pool_status(self) -> dict:
        """Summary of the pool's current state."""
        relays = self.get_relays()
        connected = sum(1 for r in relays if r.is_connected())
        return {
            "total_relays": len(relays),
            "connected": connected,
            "disconnected": len(relays) - connected,
            "read_relays": len(self.get_read_relays()),
            "write_relays": len(self.get_write_relays()),
            "relay_urls": [r.url for r in relays],
        }

    def get_relay_stats(self) -> Dict[str, dict]:
        """Return per-relay statistics."""
        return {url: relay.get_stats() for url, relay in self._relays.items()}

    def get_healthy_relays(self) -> List[RelayConnection]:
        """
        Return relays that are currently connected and have low error rates.
        """
        healthy = []
        for relay in self._relays.values():
            stats = relay.get_stats()
            errors = stats.get("errors", 0)
            received = stats.get("messages_received", 0)
            # Healthy = connected and error rate < 10% (or no messages yet)
            if relay.is_connected():
                if received == 0 or errors / received < 0.1:
                    healthy.append(relay)
        return healthy

    def find_fastest_relay(self) -> Optional[str]:
        """
        Return the URL of the relay with the lowest recorded latency.
        Falls back to returning the first connected relay.
        """
        best_url = None
        best_latency = float("inf")
        for url, relay in self._relays.items():
            stats = relay.get_stats()
            latency = stats.get("latency_ms")
            if latency is not None and latency < best_latency:
                best_latency = latency
                best_url = url

        if best_url is None:
            # Fallback: first connected relay
            for url, relay in self._relays.items():
                if relay.is_connected():
                    return url

        return best_url

    def fetch_all_info(self, timeout: int = 5) -> Dict[str, Optional[RelayInfo]]:
        """
        Fetch NIP-11 info documents from all relays.

        Returns
        -------
        dict mapping url -> RelayInfo or None
        """
        results = {}
        for url, relay in self._relays.items():
            results[url] = relay.get_info(timeout=timeout)
        return results

    def add_from_relay_list(self, relay_list: Dict[str, Dict[str, bool]]):
        """
        Populate the pool from a NIP-65 relay list dict.

        Parameters
        ----------
        relay_list : dict mapping url -> {'read': bool, 'write': bool}
        """
        for url, perms in relay_list.items():
            self.add_relay(url, read=perms.get("read", True), write=perms.get("write", True))

    def add_defaults(self):
        """Add all DEFAULT_RELAYS to the pool (read+write)."""
        for url in DEFAULT_RELAYS:
            self.add_relay(url)

    def __len__(self):
        return len(self._relays)

    def __repr__(self):
        return f"<RelayPool relays={len(self._relays)} connected={sum(1 for r in self._relays.values() if r.is_connected())}>"
