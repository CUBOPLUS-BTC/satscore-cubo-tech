# magma-sdk

Synchronous Python client for the Magma / SatScore Bitcoin API.

Stdlib-only (no `requests` dependency). Typed dataclass responses, a single
`MagmaClient` facade, automatic retries on transient failures, and a
structured exception hierarchy so callers can react to specific HTTP status
codes without string matching.

## Install

```bash
pip install -e ./sdk
```

## Quick start

```python
from magma_sdk import MagmaClient

client = MagmaClient("https://api.magma.example")

# Public endpoints
projection = client.savings.project(monthly_usd=100, years=10)
print(projection.scenarios[0].projected_value)

comparison = client.remittance.compare(amount_usd=500, frequency="monthly")
print(comparison.best_channel, comparison.annual_savings)

price = client.price.get()
print(price.price_usd, price.sources_count)

# Authenticated endpoints — Nostr (NIP-07) flow
challenge = client.auth.create_challenge(pubkey="a" * 64)
# ...have the wallet sign an event with `challenge`...
session = client.auth.verify(signed_event=signed, challenge=challenge.challenge)
# The token is stored automatically after verify().

progress = client.savings.progress()
print(progress.streak_months, progress.total_invested_usd)
```

## LNURL-auth flow

```python
ln = client.auth.create_lnurl()
print("Scan:", ln.lnurl)

while True:
    status = client.auth.lnurl_status(ln.k1)
    if status.authenticated:
        print("Logged in as", status.pubkey)
        break
```

## Error handling

```python
from magma_sdk import (
    APIError, AuthenticationError, RateLimitError, TransportError,
)

try:
    client.savings.progress()
except AuthenticationError:
    ...  # token expired — re-auth
except RateLimitError as e:
    ...  # back off; e.detail may explain why
except TransportError:
    ...  # network or DNS problem
except APIError as e:
    print(e.status, e.detail)
```

## Configuration

```python
client = MagmaClient(
    "https://api.magma.example",
    token="optional_initial_bearer",
    timeout=10.0,       # per-request seconds
    max_retries=2,      # transient failures (5xx, 429, network)
    backoff=0.25,       # exponential base, doubles each retry
    user_agent="my-app/1.0",
)
```

## Async client

`AsyncMagmaClient` mirrors the sync API and is safe to call from
`asyncio`, FastAPI handlers, etc. Under the hood it delegates to the
sync transport via `asyncio.to_thread`, so no third-party async HTTP
dependency is required.

```python
import asyncio
from magma_sdk import AsyncMagmaClient

async def main():
    async with AsyncMagmaClient("https://api.magma.example") as client:
        quote = await client.price.get()
        proj = await client.savings.project(monthly_usd=100, years=10)
        rem = await client.remittance.compare(amount_usd=500)
        print(quote.price_usd, proj.total_invested, rem.best_channel)

asyncio.run(main())
```

If you need true non-blocking throughput, wrap `httpx.AsyncClient` in
a custom transport and pass it in via `MagmaClient(transport=...)`.

## Retry-After

The transport honours an upstream `Retry-After` header (both numeric
seconds and HTTP-date forms) on any retriable status
(`408/425/429/5xx`). Values are clamped to 60s so a misbehaving server
can't stall the client indefinitely. Disable with
`MagmaClient(..., respect_retry_after=False)` via a custom
`TransportConfig` if you prefer fixed exponential backoff.

## Command-line interface

The SDK ships with a `magma` console script (also invokable as
`python -m magma_sdk`):

```bash
export MAGMA_BASE_URL=https://api.magma.example
magma price --pretty
magma savings-project --monthly-usd 100 --years 10
magma remittance --amount-usd 500 --frequency monthly | jq .annual_savings
magma pension --monthly-usd 150 --years 20
magma fees
magma alerts --limit 5
```

Authenticated commands (`savings-progress`) use `MAGMA_TOKEN` or
`--token`. Exit codes: `0` success, `1` usage/validation, `2` API
error, `3` transport error.

## Status

`v0.2`: covers public endpoints, session management, sync + async
clients, `Retry-After`, and a stdlib-only CLI. Pagination helpers and
a native async transport (for truly non-blocking I/O) are tracked for
a future release.
