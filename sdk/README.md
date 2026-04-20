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

## Webhook verification

When Magma sends signed webhooks, verify them with
`WebhookVerifier`. It checks the HMAC-SHA256 of
`"<timestamp>.<body>"` and rejects replays older than `tolerance_seconds`.

```python
from magma_sdk import WebhookVerifier, InvalidSignatureError, ReplayError

verifier = WebhookVerifier(secret="shhh", tolerance_seconds=300)

try:
    event = verifier.verify_request(body=request.body, headers=request.headers)
except (InvalidSignatureError, ReplayError):
    return 400

assert event.type == "alert.fee_low"
handle(event.data)
```

Producers (or your tests) can mint the headers with `sign_webhook`:

```python
from magma_sdk import sign_webhook
headers = sign_webhook(body, secret="shhh")
# headers = {"X-Magma-Signature": "...", "X-Magma-Timestamp": "..."}
```

## Idempotency keys

Pass `idempotency_key` to any mutation and the SDK adds an
`Idempotency-Key` header. Useful for retrying network-interrupted
deposits without risking a double-write.

```python
import uuid
key = str(uuid.uuid4())
client.savings.record_deposit(50, idempotency_key=key)
client.savings.create_goal(monthly_target_usd=100, idempotency_key=key)
```

## Request IDs and retry observability

Every outbound request carries an `X-Request-Id` header. Pass your own
via `request_id=...` to correlate with your traces. You can also subscribe
to retry events:

```python
from magma_sdk import MagmaClient, RetryEvent

def log_retry(event: RetryEvent):
    print(
        f"retry {event.method} {event.path} attempt={event.attempt} "
        f"status={event.status} delay={event.delay:.2f}s rid={event.request_id}"
    )

client = MagmaClient("https://api.magma.example", on_retry=log_retry)
```

The callback receives a :class:`RetryEvent` and never breaks the request
pipeline even if it raises.

## Alert iterators

Consume alerts as they arrive without reinventing a polling loop:

```python
# Sync
for alert in client.alerts.iter_new(since=last_seen_ts, poll_interval=5.0):
    handle(alert)

# Async
async for alert in async_client.alerts.stream(since=last_seen_ts, poll_interval=5.0):
    await handle(alert)
```

Deduplication is automatic across polls; pass `max_iterations` or a
`stop=callable` to bound the loop (tests love `max_iterations=1`).

## Health checks

```python
if client.wait_until_ready(timeout=30):
    ...
# Async
await async_client.wait_until_ready(timeout=30)
```

## Testing your code against the SDK

`magma_sdk.testing` exposes a `MockTransport` so consumers can unit-test
code that takes a `MagmaClient` without mocking HTTP by hand:

```python
from magma_sdk.testing import MockTransport, make_test_client

mock = MockTransport()
mock.on("GET", "/price", {"price_usd": 70000, "sources_count": 2, "deviation": 0, "has_warning": False})
client = make_test_client(transport=mock)

assert my_function(client) == 70000
assert mock.find("GET", "/price") is not None
```

Other helpers: `mock.enqueue(...)` for a FIFO of responses,
`mock.enqueue_error(exc)` to simulate failures, `mock.set_default(...)`
as a catch-all, `mock.find_all(...)` / `mock.reset()` for assertions.

## Liquid Network

Tap into the Liquid sidechain (Blockstream) for faster settlement and
confidential-amount Bitcoin-denominated transfers — especially useful
for remittance amounts above ~$1k where Lightning routing gets
awkward.

```python
status = client.liquid.status()
print(status.block_height, status.recommended_fee_sat_vb)

lbtc = client.liquid.lbtc()
print(lbtc.ticker, lbtc.issued_amount)

# Arbitrary asset by hex id
info = client.liquid.asset("6f0279e9ed041c3d710a9f57d0c02928416460c4b722ae3457a11eec381c526d")

# Async works too
await async_client.liquid.status()
```

CLI:

```bash
magma liquid-status
magma liquid-lbtc --pretty
magma liquid-usdt
magma liquid-asset 6f0279e9ed041c3d710a9f57d0c02928416460c4b722ae3457a11eec381c526d
```

`client.remittance.compare(...)` now returns a live Liquid channel
alongside Lightning, priced from real Liquid fee estimates.

## Status

`v0.4`: Liquid support (status, fee estimates, asset lookups, L-BTC
channel in remittance comparison), webhooks, idempotency keys, request
IDs, retry hook, alert iterators (sync + async), health/readiness,
consumer testing helpers, sync + async clients, `Retry-After`, and a
stdlib-only CLI. A native async transport and server-driven pagination
are tracked for a future release.
