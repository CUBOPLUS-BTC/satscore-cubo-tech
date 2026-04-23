"""
Nostr Protocol Library for the Magma Bitcoin app.

Implements NIP-01 through NIP-65 event handling, identity management,
relay communication helpers, and subscription filters — pure Python
standard library, no third-party dependencies.
"""

from app.nostr.events import (
    # Kind constants
    KIND_METADATA,
    KIND_TEXT_NOTE,
    KIND_RECOMMEND_RELAY,
    KIND_CONTACTS,
    KIND_ENCRYPTED_DM,
    KIND_DELETE,
    KIND_REPOST,
    KIND_REACTION,
    KIND_BADGE_AWARD,
    KIND_CHANNEL_CREATE,
    KIND_CHANNEL_METADATA,
    KIND_CHANNEL_MESSAGE,
    KIND_CHANNEL_HIDE,
    KIND_CHANNEL_MUTE,
    KIND_REPORT,
    KIND_ZAP_REQUEST,
    KIND_ZAP_RECEIPT,
    KIND_MUTE_LIST,
    KIND_PIN_LIST,
    KIND_RELAY_LIST,
    KIND_BOOKMARKS,
    KIND_COMMUNITIES,
    KIND_STALL,
    KIND_PRODUCT,
    KIND_ARTICLE,
    KIND_DRAFT,
    KIND_APP_SPECIFIC,
    KIND_AUTH,
    KIND_HTTP_AUTH,
    EVENT_KIND_NAMES,
    # Classes
    NostrEvent,
    EventBuilder,
    EventValidator,
)

from app.nostr.nips import (
    serialize_event,
    compute_event_id,
    parse_contact_list,
    build_contact_list,
    merge_contact_lists,
    parse_nip05,
    build_nip05_json,
    validate_nip05_format,
    parse_thread_tags,
    build_reply_tags,
    get_thread_depth,
    count_leading_zero_bits,
    meets_difficulty,
    mine_event,
    encode_npub,
    decode_npub,
    encode_note,
    decode_note,
    encode_nprofile,
    decode_nprofile,
    encode_nevent,
    decode_nevent,
    encode_naddr,
    decode_naddr,
    parse_reaction,
    build_reaction,
    REACTION_TYPES,
    mark_sensitive,
    is_sensitive,
    set_expiration,
    is_expired,
    get_expiration,
    create_zap_request,
    validate_zap_request,
    parse_zap_receipt,
    validate_zap_receipt,
    get_zap_amount,
    parse_relay_list,
    build_relay_list,
    get_read_relays,
    get_write_relays,
)

from app.nostr.filters import (
    Filter,
    FilterBuilder,
    SubscriptionManager,
)

from app.nostr.relay import (
    DEFAULT_RELAYS,
    RelayInfo,
    RelayMessage,
    RelayConnection,
    RelayPool,
)

from app.nostr.identity import (
    NostrIdentity,
    IdentityManager,
    ProfileValidator,
)

__all__ = [
    # Kind constants
    "KIND_METADATA", "KIND_TEXT_NOTE", "KIND_RECOMMEND_RELAY",
    "KIND_CONTACTS", "KIND_ENCRYPTED_DM", "KIND_DELETE",
    "KIND_REPOST", "KIND_REACTION", "KIND_BADGE_AWARD",
    "KIND_CHANNEL_CREATE", "KIND_CHANNEL_METADATA", "KIND_CHANNEL_MESSAGE",
    "KIND_CHANNEL_HIDE", "KIND_CHANNEL_MUTE",
    "KIND_REPORT", "KIND_ZAP_REQUEST", "KIND_ZAP_RECEIPT",
    "KIND_MUTE_LIST", "KIND_PIN_LIST", "KIND_RELAY_LIST",
    "KIND_BOOKMARKS", "KIND_COMMUNITIES",
    "KIND_STALL", "KIND_PRODUCT", "KIND_ARTICLE", "KIND_DRAFT",
    "KIND_APP_SPECIFIC", "KIND_AUTH", "KIND_HTTP_AUTH",
    "EVENT_KIND_NAMES",
    # Event classes
    "NostrEvent", "EventBuilder", "EventValidator",
    # NIP helpers
    "serialize_event", "compute_event_id",
    "parse_contact_list", "build_contact_list", "merge_contact_lists",
    "parse_nip05", "build_nip05_json", "validate_nip05_format",
    "parse_thread_tags", "build_reply_tags", "get_thread_depth",
    "count_leading_zero_bits", "meets_difficulty", "mine_event",
    "encode_npub", "decode_npub", "encode_note", "decode_note",
    "encode_nprofile", "decode_nprofile",
    "encode_nevent", "decode_nevent",
    "encode_naddr", "decode_naddr",
    "parse_reaction", "build_reaction", "REACTION_TYPES",
    "mark_sensitive", "is_sensitive",
    "set_expiration", "is_expired", "get_expiration",
    "create_zap_request", "validate_zap_request",
    "parse_zap_receipt", "validate_zap_receipt", "get_zap_amount",
    "parse_relay_list", "build_relay_list", "get_read_relays", "get_write_relays",
    # Filters
    "Filter", "FilterBuilder", "SubscriptionManager",
    # Relay
    "DEFAULT_RELAYS", "RelayInfo", "RelayMessage", "RelayConnection", "RelayPool",
    # Identity
    "NostrIdentity", "IdentityManager", "ProfileValidator",
]
