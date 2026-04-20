"""Command-line interface for the Magma SDK.

Usage::

    python -m magma_sdk --base-url URL <command> [args...]

Commands map one-to-one to the public SDK endpoints. Results are
printed as JSON on stdout so the CLI composes cleanly with ``jq``
and other Unix tools. Errors go to stderr with a non-zero exit code.

Environment variables:
    MAGMA_BASE_URL   default for --base-url
    MAGMA_TOKEN      default for --token
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from typing import Any, List, Optional, Sequence

from . import __version__
from .client import MagmaClient
from .exceptions import APIError, MagmaError, TransportError


def _to_jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        out = {}
        for field in dataclasses.fields(value):
            if field.name == "raw":
                continue
            out[field.name] = _to_jsonable(getattr(value, field.name))
        return out
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    return value


def _print_json(value: Any, pretty: bool) -> None:
    data = _to_jsonable(value)
    if pretty:
        sys.stdout.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(json.dumps(data) + "\n")
    sys.stdout.flush()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="magma",
        description="Command-line interface for the Magma SDK.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("MAGMA_BASE_URL"),
        help="API base URL (default: $MAGMA_BASE_URL)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("MAGMA_TOKEN"),
        help="Bearer token (default: $MAGMA_TOKEN)",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Indent and sort JSON output",
    )
    parser.add_argument("--version", action="version", version=f"magma-sdk {__version__}")

    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    # price
    sub.add_parser("price", help="Fetch the verified BTC price")

    # savings project
    sp = sub.add_parser("savings-project", help="Run a DCA savings projection")
    sp.add_argument("--monthly-usd", type=float, required=True)
    sp.add_argument("--years", type=int, default=10)

    # savings progress (auth)
    sub.add_parser(
        "savings-progress",
        help="Show the authenticated user's savings progress",
    )

    # pension projection
    pp = sub.add_parser("pension", help="Run a pension projection")
    pp.add_argument("--monthly-usd", type=float, required=True)
    pp.add_argument("--years", type=int, required=True)

    # remittance
    rc = sub.add_parser("remittance", help="Compare remittance channels")
    rc.add_argument("--amount-usd", type=float, required=True)
    rc.add_argument(
        "--frequency",
        choices=("monthly", "biweekly", "weekly"),
        default="monthly",
    )

    sub.add_parser("fees", help="Current on-chain fee snapshot")

    al = sub.add_parser("alerts", help="Recent alerts")
    al.add_argument("--limit", type=int, default=20)

    sub.add_parser("alerts-status", help="Alert monitor status")
    sub.add_parser("network", help="Bitcoin network status")

    sub.add_parser("liquid-status", help="Liquid Network tip + fees")
    sub.add_parser("liquid-lbtc", help="L-BTC asset info")
    sub.add_parser("liquid-usdt", help="USDt on Liquid asset info")
    la = sub.add_parser("liquid-asset", help="Arbitrary Liquid asset lookup")
    la.add_argument("asset_id")

    return parser


def _make_client(args: argparse.Namespace) -> MagmaClient:
    if not args.base_url:
        raise MagmaError(
            "base URL is required (pass --base-url or set MAGMA_BASE_URL)"
        )
    client = MagmaClient(
        args.base_url,
        token=args.token,
        timeout=args.timeout,
        max_retries=args.retries,
    )
    return client


def _dispatch(client: MagmaClient, args: argparse.Namespace) -> Any:
    cmd = args.command
    if cmd == "price":
        return client.price.get()
    if cmd == "savings-project":
        return client.savings.project(
            monthly_usd=args.monthly_usd, years=args.years
        )
    if cmd == "savings-progress":
        return client.savings.progress()
    if cmd == "pension":
        return client.pension.project(
            monthly_saving_usd=args.monthly_usd, years=args.years
        )
    if cmd == "remittance":
        return client.remittance.compare(
            amount_usd=args.amount_usd, frequency=args.frequency
        )
    if cmd == "fees":
        return client.remittance.fees()
    if cmd == "alerts":
        return client.alerts.list(limit=args.limit)
    if cmd == "alerts-status":
        return client.alerts.status()
    if cmd == "network":
        return client.network.status()
    if cmd == "liquid-status":
        return client.liquid.status()
    if cmd == "liquid-lbtc":
        return client.liquid.lbtc()
    if cmd == "liquid-usdt":
        return client.liquid.usdt()
    if cmd == "liquid-asset":
        return client.liquid.asset(args.asset_id)
    raise MagmaError(f"Unknown command: {cmd}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        client = _make_client(args)
        result = _dispatch(client, args)
    except APIError as exc:
        sys.stderr.write(f"API error {exc.status}: {exc.detail or exc}\n")
        return 2
    except TransportError as exc:
        sys.stderr.write(f"Transport error: {exc}\n")
        return 3
    except MagmaError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1

    _print_json(result, args.pretty)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
