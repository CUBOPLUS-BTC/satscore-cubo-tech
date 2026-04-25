"""API schema definitions for the Magma OpenAPI specification.

Each entry in ``ENDPOINT_SCHEMAS`` describes one HTTP operation.  The
dict structure mirrors an OpenAPI 3.0 path-item / operation object so
``generator.py`` can assemble the full spec with minimal transformation.

Keys per operation
------------------
path        : str   – URL path, e.g. "/auth/challenge"
method      : str   – HTTP verb (lowercase)
summary     : str   – Short (< 80 chars) description
description : str   – Longer prose explanation
tags        : list  – Grouping tags for the Swagger UI sidebar
auth_required : bool – Whether a Bearer or Nostr NIP-98 token is needed
parameters  : list  – Query / path parameters (OpenAPI Parameter Object)
request_body: dict|None – OpenAPI Request Body Object
responses   : dict  – OpenAPI Responses Object
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Reusable inline schema fragments
# ---------------------------------------------------------------------------

_PUBKEY_SCHEMA = {
    "type": "string",
    "pattern": "^[0-9a-f]{64}$",
    "description": "Nostr public key (64-character lowercase hex).",
    "example": "3bf0c63fcb93463407af97a5e5ee64fa883d107ef9e558472c4eb9aaaefa459d",
}

_BTC_ADDRESS_SCHEMA = {
    "type": "string",
    "description": "Bitcoin address (Legacy, SegWit, or Taproot).",
    "example": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
}

_TIMESTAMP_SCHEMA = {
    "type": "integer",
    "format": "int64",
    "description": "Unix timestamp (seconds since epoch).",
    "example": 1700000000,
}

_ERROR_RESPONSE = {
    "description": "Error response",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "detail": {"type": "string", "description": "Human-readable error message."},
                },
                "required": ["detail"],
            }
        }
    },
}

_AUTH_HEADER_PARAM = {
    "name": "Authorization",
    "in": "header",
    "required": True,
    "schema": {"type": "string"},
    "description": "Bearer <token> or Nostr <base64-event>.",
}

_LIMIT_PARAM = {
    "name": "limit",
    "in": "query",
    "required": False,
    "schema": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
    "description": "Maximum number of results to return.",
}

_OFFSET_PARAM = {
    "name": "offset",
    "in": "query",
    "required": False,
    "schema": {"type": "integer", "default": 0, "minimum": 0},
    "description": "Number of results to skip (pagination).",
}

# ---------------------------------------------------------------------------
# Endpoint definitions
# ---------------------------------------------------------------------------

ENDPOINT_SCHEMAS: list[dict] = [

    # ===================================================================
    # AUTH
    # ===================================================================
    {
        "path": "/auth/challenge",
        "method": "post",
        "summary": "Request a Nostr authentication challenge",
        "description": (
            "Generates a random 32-byte hex challenge for the given pubkey.  "
            "The client must sign the challenge with their Nostr private key "
            "and submit the signed event to ``POST /auth/verify``."
        ),
        "tags": ["Authentication"],
        "auth_required": False,
        "parameters": [],
        "request_body": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["pubkey"],
                        "properties": {
                            "pubkey": _PUBKEY_SCHEMA,
                        },
                    }
                }
            },
        },
        "responses": {
            "200": {
                "description": "Challenge created",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "challenge": {
                                    "type": "string",
                                    "description": "64-char hex challenge string.",
                                },
                                "created_at": _TIMESTAMP_SCHEMA,
                            },
                        }
                    }
                },
            },
            "400": _ERROR_RESPONSE,
            "429": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/auth/verify",
        "method": "post",
        "summary": "Verify a signed Nostr event and obtain a session token",
        "description": (
            "Accepts a NIP-07 signed event.  On success returns a Bearer token "
            "valid for 24 hours."
        ),
        "tags": ["Authentication"],
        "auth_required": False,
        "parameters": [],
        "request_body": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["signed_event", "challenge"],
                        "properties": {
                            "signed_event": {
                                "type": "object",
                                "description": "Complete Nostr event object (kind 22242).",
                            },
                            "challenge": {
                                "type": "string",
                                "description": "Challenge obtained from /auth/challenge.",
                            },
                        },
                    }
                }
            },
        },
        "responses": {
            "200": {
                "description": "Authentication successful",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "status": {"type": "string", "example": "ok"},
                                "token": {"type": "string"},
                                "pubkey": _PUBKEY_SCHEMA,
                            },
                        }
                    }
                },
            },
            "401": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/auth/me",
        "method": "get",
        "summary": "Verify the current session token",
        "description": "Returns the authenticated pubkey if the token is valid.",
        "tags": ["Authentication"],
        "auth_required": True,
        "parameters": [_AUTH_HEADER_PARAM],
        "request_body": None,
        "responses": {
            "200": {
                "description": "Session is valid",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "pubkey": _PUBKEY_SCHEMA,
                                "created_at": _TIMESTAMP_SCHEMA,
                            },
                        }
                    }
                },
            },
            "401": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/auth/lnurl",
        "method": "post",
        "summary": "Generate an LNURL-auth QR challenge",
        "description": "Returns a bech32-encoded LNURL that a Lightning wallet can scan to authenticate.",
        "tags": ["Authentication"],
        "auth_required": False,
        "parameters": [],
        "request_body": None,
        "responses": {
            "200": {
                "description": "LNURL challenge created",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "lnurl": {"type": "string", "description": "bech32-encoded LNURL."},
                                "k1": {"type": "string", "description": "Raw hex challenge."},
                                "expires_at": _TIMESTAMP_SCHEMA,
                            },
                        }
                    }
                },
            },
        },
    },

    {
        "path": "/auth/lnurl-callback",
        "method": "get",
        "summary": "LNURL-auth wallet callback",
        "description": "Called by Lightning wallets after signing the k1 challenge.",
        "tags": ["Authentication"],
        "auth_required": False,
        "parameters": [
            {"name": "tag",  "in": "query", "required": True,  "schema": {"type": "string", "enum": ["login"]}},
            {"name": "k1",   "in": "query", "required": True,  "schema": {"type": "string"}},
            {"name": "sig",  "in": "query", "required": True,  "schema": {"type": "string"}},
            {"name": "key",  "in": "query", "required": True,  "schema": {"type": "string"}},
        ],
        "request_body": None,
        "responses": {
            "200": {
                "description": "Standard LNURL response",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "status": {"type": "string", "enum": ["OK", "ERROR"]},
                                "reason": {"type": "string"},
                            },
                        }
                    }
                },
            },
        },
    },

    {
        "path": "/auth/lnurl-status",
        "method": "get",
        "summary": "Poll LNURL-auth completion status",
        "description": "Frontend polls this until the wallet has completed authentication.",
        "tags": ["Authentication"],
        "auth_required": False,
        "parameters": [
            {"name": "k1", "in": "query", "required": True, "schema": {"type": "string"}},
        ],
        "request_body": None,
        "responses": {
            "200": {
                "description": "Current LNURL status",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "status": {"type": "string", "enum": ["pending", "verified", "expired"]},
                                "token": {"type": "string", "nullable": True},
                                "pubkey": {**_PUBKEY_SCHEMA, "nullable": True},
                            },
                        }
                    }
                },
            },
            "400": _ERROR_RESPONSE,
        },
    },

    # ===================================================================
    # SCORING
    # ===================================================================
    {
        "path": "/score",
        "method": "post",
        "summary": "Full Bitcoin address analysis",
        "description": (
            "Performs a comprehensive on-chain analysis of a Bitcoin address and "
            "returns a composite score with grade and per-dimension breakdown."
        ),
        "tags": ["Scoring"],
        "auth_required": False,
        "parameters": [],
        "request_body": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["address"],
                        "properties": {
                            "address": _BTC_ADDRESS_SCHEMA,
                        },
                    }
                }
            },
        },
        "responses": {
            "200": {
                "description": "Address analysis result",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/AddressScore"},
                    }
                },
            },
            "400": _ERROR_RESPONSE,
            "422": _ERROR_RESPONSE,
            "502": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/score/summary",
        "method": "get",
        "summary": "Lightweight address score summary",
        "description": "Returns only total_score, grade, and recommendations.",
        "tags": ["Scoring"],
        "auth_required": False,
        "parameters": [
            {"name": "address", "in": "query", "required": True, "schema": _BTC_ADDRESS_SCHEMA},
        ],
        "request_body": None,
        "responses": {
            "200": {
                "description": "Score summary",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ScoreSummary"},
                    }
                },
            },
            "400": _ERROR_RESPONSE,
            "422": _ERROR_RESPONSE,
        },
    },

    # ===================================================================
    # PREFERENCES
    # ===================================================================
    {
        "path": "/preferences",
        "method": "get",
        "summary": "Get user alert preferences",
        "description": "Returns the authenticated user's fee and price alert thresholds.",
        "tags": ["Preferences"],
        "auth_required": True,
        "parameters": [_AUTH_HEADER_PARAM],
        "request_body": None,
        "responses": {
            "200": {
                "description": "User preferences",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/UserPreferences"},
                    }
                },
            },
            "401": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/preferences",
        "method": "put",
        "summary": "Update user alert preferences",
        "description": "Set fee alert thresholds, price alerts, and global alert toggle.",
        "tags": ["Preferences"],
        "auth_required": True,
        "parameters": [_AUTH_HEADER_PARAM],
        "request_body": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/UserPreferencesUpdate"},
                }
            },
        },
        "responses": {
            "200": {
                "description": "Updated preferences",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/UserPreferences"},
                    }
                },
            },
            "400": _ERROR_RESPONSE,
            "401": _ERROR_RESPONSE,
        },
    },

    # ===================================================================
    # SAVINGS
    # ===================================================================
    {
        "path": "/savings/goal",
        "method": "get",
        "summary": "Get savings goal configuration",
        "description": "Returns the user's monthly savings target and projection horizon.",
        "tags": ["Savings"],
        "auth_required": True,
        "parameters": [_AUTH_HEADER_PARAM],
        "request_body": None,
        "responses": {
            "200": {
                "description": "Savings goal",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/SavingsGoal"},
                    }
                },
            },
            "401": _ERROR_RESPONSE,
            "404": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/savings/goal",
        "method": "post",
        "summary": "Create or update savings goal",
        "description": "Set the monthly USD savings target and projection horizon in years.",
        "tags": ["Savings"],
        "auth_required": True,
        "parameters": [_AUTH_HEADER_PARAM],
        "request_body": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["monthly_target_usd"],
                        "properties": {
                            "monthly_target_usd": {
                                "type": "number",
                                "minimum": 1,
                                "description": "Monthly savings target in USD.",
                                "example": 100,
                            },
                            "target_years": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 50,
                                "default": 10,
                                "description": "Projection horizon in years.",
                            },
                        },
                    }
                }
            },
        },
        "responses": {
            "200": {"description": "Goal created/updated", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SavingsGoal"}}}},
            "400": _ERROR_RESPONSE,
            "401": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/savings/deposit",
        "method": "post",
        "summary": "Record a Bitcoin savings deposit",
        "description": "Log a new deposit with its USD value and current BTC price.",
        "tags": ["Savings"],
        "auth_required": True,
        "parameters": [_AUTH_HEADER_PARAM],
        "request_body": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["amount_usd", "btc_price"],
                        "properties": {
                            "amount_usd": {"type": "number", "minimum": 0.01},
                            "btc_price": {"type": "number", "minimum": 1},
                        },
                    }
                }
            },
        },
        "responses": {
            "201": {"description": "Deposit recorded"},
            "400": _ERROR_RESPONSE,
            "401": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/savings/projection",
        "method": "get",
        "summary": "Get savings projection",
        "description": "Returns current balance, projection, and goal completion percentage.",
        "tags": ["Savings"],
        "auth_required": True,
        "parameters": [_AUTH_HEADER_PARAM],
        "request_body": None,
        "responses": {
            "200": {"description": "Savings projection"},
            "401": _ERROR_RESPONSE,
        },
    },

    # ===================================================================
    # PENSION
    # ===================================================================
    {
        "path": "/pension/projection",
        "method": "get",
        "summary": "Bitcoin pension projection",
        "description": "Returns a long-term BTC accumulation projection based on DCA parameters.",
        "tags": ["Pension"],
        "auth_required": True,
        "parameters": [
            _AUTH_HEADER_PARAM,
            {"name": "monthly_usd", "in": "query", "required": False, "schema": {"type": "number"}},
            {"name": "years",       "in": "query", "required": False, "schema": {"type": "integer"}},
        ],
        "request_body": None,
        "responses": {
            "200": {"description": "Pension projection data"},
            "401": _ERROR_RESPONSE,
        },
    },

    # ===================================================================
    # REMITTANCE
    # ===================================================================
    {
        "path": "/remittance/quote",
        "method": "post",
        "summary": "Get a Bitcoin remittance quote",
        "description": "Returns estimated fees and final receive amount for a remittance.",
        "tags": ["Remittance"],
        "auth_required": False,
        "parameters": [],
        "request_body": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["amount_usd", "destination_country"],
                        "properties": {
                            "amount_usd": {"type": "number", "minimum": 1},
                            "destination_country": {"type": "string", "example": "SV"},
                        },
                    }
                }
            },
        },
        "responses": {
            "200": {"description": "Remittance quote"},
            "400": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/remittance/projection",
        "method": "get",
        "summary": "Multi-year remittance savings projection",
        "description": "Compare cumulative costs of traditional remittance vs Bitcoin over time.",
        "tags": ["Remittance"],
        "auth_required": False,
        "parameters": [
            {"name": "monthly_usd",          "in": "query", "required": True, "schema": {"type": "number"}},
            {"name": "years",                "in": "query", "required": False, "schema": {"type": "integer", "default": 5}},
            {"name": "destination_country",  "in": "query", "required": False, "schema": {"type": "string", "default": "SV"}},
        ],
        "request_body": None,
        "responses": {
            "200": {"description": "Remittance projection"},
            "400": _ERROR_RESPONSE,
        },
    },

    # ===================================================================
    # LIGHTNING
    # ===================================================================
    {
        "path": "/lightning/stats",
        "method": "get",
        "summary": "Lightning Network statistics",
        "description": "Returns current channel count, node count, total capacity, and average fee rate.",
        "tags": ["Lightning"],
        "auth_required": False,
        "parameters": [],
        "request_body": None,
        "responses": {
            "200": {"description": "Lightning stats"},
            "502": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/lightning/nodes/top",
        "method": "get",
        "summary": "Top Lightning nodes by capacity",
        "description": "Returns the highest-capacity public Lightning nodes.",
        "tags": ["Lightning"],
        "auth_required": False,
        "parameters": [_LIMIT_PARAM],
        "request_body": None,
        "responses": {
            "200": {"description": "Top nodes list"},
            "502": _ERROR_RESPONSE,
        },
    },

    # ===================================================================
    # NETWORK (mempool / fees)
    # ===================================================================
    {
        "path": "/network/fees",
        "method": "get",
        "summary": "Current Bitcoin network fee estimates",
        "description": "Returns sat/vbyte estimates for fastest, half-hour, and economy confirmation.",
        "tags": ["Network"],
        "auth_required": False,
        "parameters": [],
        "request_body": None,
        "responses": {
            "200": {
                "description": "Fee estimates",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "fastestFee":   {"type": "integer", "description": "sat/vbyte for next block."},
                                "halfHourFee":  {"type": "integer"},
                                "hourFee":      {"type": "integer"},
                                "economyFee":   {"type": "integer"},
                                "minimumFee":   {"type": "integer"},
                            },
                        }
                    }
                },
            },
            "502": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/network/mempool",
        "method": "get",
        "summary": "Mempool statistics",
        "description": "Returns current mempool size, transaction count, and vsize.",
        "tags": ["Network"],
        "auth_required": False,
        "parameters": [],
        "request_body": None,
        "responses": {
            "200": {"description": "Mempool stats"},
            "502": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/network/blocks",
        "method": "get",
        "summary": "Recent Bitcoin blocks",
        "description": "Returns the most recently mined blocks.",
        "tags": ["Network"],
        "auth_required": False,
        "parameters": [_LIMIT_PARAM],
        "request_body": None,
        "responses": {
            "200": {"description": "Recent blocks"},
        },
    },

    # ===================================================================
    # ANALYTICS
    # ===================================================================
    {
        "path": "/analytics/summary",
        "method": "get",
        "summary": "User activity summary",
        "description": "Returns aggregated event counts, retention data, and feature usage for the authenticated user.",
        "tags": ["Analytics"],
        "auth_required": True,
        "parameters": [
            _AUTH_HEADER_PARAM,
            {"name": "days", "in": "query", "required": False, "schema": {"type": "integer", "default": 30}},
        ],
        "request_body": None,
        "responses": {
            "200": {"description": "Activity summary"},
            "401": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/analytics/events",
        "method": "post",
        "summary": "Record an analytics event",
        "description": "Client-side event tracking for feature usage metrics.",
        "tags": ["Analytics"],
        "auth_required": True,
        "parameters": [_AUTH_HEADER_PARAM],
        "request_body": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["event_type"],
                        "properties": {
                            "event_type": {"type": "string"},
                            "properties": {"type": "object"},
                        },
                    }
                }
            },
        },
        "responses": {
            "200": {"description": "Event recorded"},
            "401": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/analytics/platform",
        "method": "get",
        "summary": "Platform-wide statistics (admin)",
        "description": "Returns aggregate user counts, event totals, and feature adoption metrics.",
        "tags": ["Analytics"],
        "auth_required": True,
        "parameters": [_AUTH_HEADER_PARAM],
        "request_body": None,
        "responses": {
            "200": {"description": "Platform stats"},
            "401": _ERROR_RESPONSE,
            "403": _ERROR_RESPONSE,
        },
    },

    # ===================================================================
    # GAMIFICATION
    # ===================================================================
    {
        "path": "/gamification/achievements",
        "method": "get",
        "summary": "List user achievements",
        "description": "Returns all achievements earned by the authenticated user.",
        "tags": ["Gamification"],
        "auth_required": True,
        "parameters": [_AUTH_HEADER_PARAM],
        "request_body": None,
        "responses": {
            "200": {"description": "Achievements list"},
            "401": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/gamification/leaderboard",
        "method": "get",
        "summary": "Global leaderboard",
        "description": "Returns top users ranked by score or savings metrics.",
        "tags": ["Gamification"],
        "auth_required": False,
        "parameters": [_LIMIT_PARAM],
        "request_body": None,
        "responses": {
            "200": {"description": "Leaderboard entries"},
        },
    },

    # ===================================================================
    # EXPORT
    # ===================================================================
    {
        "path": "/export/savings",
        "method": "get",
        "summary": "Export savings data as PDF",
        "description": "Generates and returns a PDF report of the user's savings history and projection.",
        "tags": ["Export"],
        "auth_required": True,
        "parameters": [_AUTH_HEADER_PARAM],
        "request_body": None,
        "responses": {
            "200": {
                "description": "PDF file",
                "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
            },
            "401": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/export/pension",
        "method": "get",
        "summary": "Export pension projection as PDF",
        "description": "Generates a PDF of the long-term Bitcoin pension projection.",
        "tags": ["Export"],
        "auth_required": True,
        "parameters": [_AUTH_HEADER_PARAM],
        "request_body": None,
        "responses": {
            "200": {
                "description": "PDF file",
                "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
            },
            "401": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/export/remittance",
        "method": "get",
        "summary": "Export remittance comparison as PDF",
        "description": "Generates a PDF comparing traditional vs Bitcoin remittance costs.",
        "tags": ["Export"],
        "auth_required": True,
        "parameters": [_AUTH_HEADER_PARAM],
        "request_body": None,
        "responses": {
            "200": {
                "description": "PDF file",
                "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
            },
            "401": _ERROR_RESPONSE,
        },
    },

    # ===================================================================
    # ALERTS
    # ===================================================================
    {
        "path": "/alerts",
        "method": "get",
        "summary": "Get current network alerts",
        "description": "Returns active fee and price alerts for the authenticated user.",
        "tags": ["Alerts"],
        "auth_required": True,
        "parameters": [_AUTH_HEADER_PARAM],
        "request_body": None,
        "responses": {
            "200": {"description": "Active alerts"},
            "401": _ERROR_RESPONSE,
        },
    },

    # ===================================================================
    # WEBHOOKS
    # ===================================================================
    {
        "path": "/webhooks",
        "method": "get",
        "summary": "List webhook subscriptions",
        "description": "Returns all webhook subscriptions for the authenticated user.",
        "tags": ["Webhooks"],
        "auth_required": True,
        "parameters": [_AUTH_HEADER_PARAM],
        "request_body": None,
        "responses": {
            "200": {
                "description": "Subscriptions list",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/WebhookSubscriptionList"},
                    }
                },
            },
            "401": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/webhooks/subscribe",
        "method": "post",
        "summary": "Create a webhook subscription",
        "description": "Register a callback URL to receive events when specific actions occur.",
        "tags": ["Webhooks"],
        "auth_required": True,
        "parameters": [_AUTH_HEADER_PARAM],
        "request_body": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/WebhookSubscribeRequest"},
                }
            },
        },
        "responses": {
            "201": {
                "description": "Subscription created",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/WebhookSubscribeResponse"},
                    }
                },
            },
            "400": _ERROR_RESPONSE,
            "401": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/webhooks/unsubscribe",
        "method": "post",
        "summary": "Delete a webhook subscription",
        "description": "Remove a webhook subscription by ID.",
        "tags": ["Webhooks"],
        "auth_required": True,
        "parameters": [_AUTH_HEADER_PARAM],
        "request_body": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["subscription_id"],
                        "properties": {
                            "subscription_id": {"type": "string"},
                        },
                    }
                }
            },
        },
        "responses": {
            "200": {"description": "Subscription deleted"},
            "401": _ERROR_RESPONSE,
            "403": _ERROR_RESPONSE,
            "404": _ERROR_RESPONSE,
        },
    },

    {
        "path": "/webhooks/test",
        "method": "post",
        "summary": "Send a test webhook",
        "description": "Triggers an immediate test delivery to the specified subscription URL.",
        "tags": ["Webhooks"],
        "auth_required": True,
        "parameters": [_AUTH_HEADER_PARAM],
        "request_body": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["subscription_id"],
                        "properties": {
                            "subscription_id": {"type": "string"},
                        },
                    }
                }
            },
        },
        "responses": {
            "200": {"description": "Test delivered"},
            "401": _ERROR_RESPONSE,
            "404": _ERROR_RESPONSE,
            "502": _ERROR_RESPONSE,
        },
    },

    # ===================================================================
    # DOCS / OpenAPI
    # ===================================================================
    {
        "path": "/openapi.json",
        "method": "get",
        "summary": "OpenAPI 3.0 specification (JSON)",
        "description": "Returns the machine-readable OpenAPI specification for this API.",
        "tags": ["Documentation"],
        "auth_required": False,
        "parameters": [],
        "request_body": None,
        "responses": {
            "200": {
                "description": "OpenAPI JSON spec",
                "content": {"application/json": {}},
            },
        },
    },

    {
        "path": "/docs",
        "method": "get",
        "summary": "Swagger UI",
        "description": "Interactive browser-based API documentation.",
        "tags": ["Documentation"],
        "auth_required": False,
        "parameters": [],
        "request_body": None,
        "responses": {
            "200": {
                "description": "Swagger UI HTML",
                "content": {"text/html": {}},
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Component schemas referenced by $ref in endpoint definitions above
# ---------------------------------------------------------------------------

COMPONENT_SCHEMAS: dict = {
    "AddressScore": {
        "type": "object",
        "description": "Full Bitcoin address analysis result.",
        "properties": {
            "address":         {"type": "string"},
            "total_score":     {"type": "number", "minimum": 0, "maximum": 100},
            "grade":           {"type": "string", "enum": ["A+", "A", "B", "C", "D", "F"]},
            "activity_score":  {"type": "number"},
            "hodl_score":      {"type": "number"},
            "diversity_score": {"type": "number"},
            "tx_count":        {"type": "integer"},
            "balance_btc":     {"type": "number"},
            "recommendations": {"type": "array", "items": {"type": "string"}},
            "analyzed_at":     _TIMESTAMP_SCHEMA,
        },
    },

    "ScoreSummary": {
        "type": "object",
        "properties": {
            "address":         {"type": "string"},
            "total_score":     {"type": "number"},
            "grade":           {"type": "string"},
            "activity_score":  {"type": "number"},
            "hodl_score":      {"type": "number"},
            "diversity_score": {"type": "number"},
            "recommendations": {"type": "array", "items": {"type": "string"}},
            "analyzed_at":     _TIMESTAMP_SCHEMA,
        },
    },

    "UserPreferences": {
        "type": "object",
        "properties": {
            "pubkey":          _PUBKEY_SCHEMA,
            "fee_alert_low":   {"type": "integer", "description": "Low fee threshold (sat/vbyte)."},
            "fee_alert_high":  {"type": "integer", "description": "High fee threshold (sat/vbyte)."},
            "price_alerts":    {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "price":     {"type": "number"},
                        "direction": {"type": "string", "enum": ["above", "below"]},
                    },
                },
            },
            "alerts_enabled":  {"type": "boolean"},
            "updated_at":      _TIMESTAMP_SCHEMA,
        },
    },

    "UserPreferencesUpdate": {
        "type": "object",
        "properties": {
            "fee_alert_low":  {"type": "integer", "minimum": 1},
            "fee_alert_high": {"type": "integer", "minimum": 1},
            "price_alerts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["price", "direction"],
                    "properties": {
                        "price":     {"type": "number"},
                        "direction": {"type": "string", "enum": ["above", "below"]},
                    },
                },
            },
            "alerts_enabled": {"type": "boolean"},
        },
    },

    "SavingsGoal": {
        "type": "object",
        "properties": {
            "pubkey":             _PUBKEY_SCHEMA,
            "monthly_target_usd": {"type": "number"},
            "target_years":       {"type": "integer"},
            "created_at":         _TIMESTAMP_SCHEMA,
            "updated_at":         _TIMESTAMP_SCHEMA,
        },
    },

    "WebhookSubscription": {
        "type": "object",
        "properties": {
            "id":                {"type": "string"},
            "pubkey":            _PUBKEY_SCHEMA,
            "url":               {"type": "string", "format": "uri"},
            "events":            {"type": "array", "items": {"type": "string"}},
            "active":            {"type": "boolean"},
            "created_at":        _TIMESTAMP_SCHEMA,
            "last_triggered_at": {**_TIMESTAMP_SCHEMA, "nullable": True},
            "failure_count":     {"type": "integer"},
        },
    },

    "WebhookSubscriptionList": {
        "type": "object",
        "properties": {
            "subscriptions":    {"type": "array", "items": {"$ref": "#/components/schemas/WebhookSubscription"}},
            "count":            {"type": "integer"},
            "supported_events": {"type": "array", "items": {"type": "string"}},
        },
    },

    "WebhookSubscribeRequest": {
        "type": "object",
        "required": ["url", "events"],
        "properties": {
            "url":    {"type": "string", "format": "uri"},
            "events": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "secret": {"type": "string", "description": "Optional custom signing secret."},
        },
    },

    "WebhookSubscribeResponse": {
        "type": "object",
        "properties": {
            "id":         {"type": "string"},
            "url":        {"type": "string"},
            "events":     {"type": "array", "items": {"type": "string"}},
            "active":     {"type": "boolean"},
            "created_at": _TIMESTAMP_SCHEMA,
            "secret":     {
                "type": "string",
                "description": "Signing secret — shown only once at creation.",
            },
            "message": {"type": "string"},
        },
    },
}
