"""
Magma Admin CLI — entry point and argument parser.

Usage::

    python -m app.cli.admin --help
    python -m app.cli.admin db status
    python -m app.cli.admin db migrate
    python -m app.cli.admin db rollback 0003
    python -m app.cli.admin user list [--limit 20] [--offset 0]
    python -m app.cli.admin user info <pubkey>
    python -m app.cli.admin user delete <pubkey>
    python -m app.cli.admin session list
    python -m app.cli.admin session cleanup
    python -m app.cli.admin stats achievements
    python -m app.cli.admin stats savings
    python -m app.cli.admin price check
    python -m app.cli.admin alerts [--limit 50]
    python -m app.cli.admin health
    python -m app.cli.admin export users [--format json|csv] [--output path]
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Optional

# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------

_COLOURS_ENABLED = sys.stdout.isatty() and os.name != "nt"


def _c(code: str, text: str) -> str:
    """Wrap *text* in an ANSI colour code if the terminal supports it."""
    if not _COLOURS_ENABLED:
        return text
    codes = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "cyan": "\033[36m",
        "bold": "\033[1m",
        "reset": "\033[0m",
    }
    return f"{codes.get(code, '')}{text}{codes['reset']}"


def ok(msg: str) -> str:
    return _c("green", f"✓ {msg}")


def err(msg: str) -> str:
    return _c("red", f"✗ {msg}")


def warn(msg: str) -> str:
    return _c("yellow", f"⚠ {msg}")


def header(msg: str) -> str:
    return _c("bold", msg)


# ---------------------------------------------------------------------------
# Table rendering
# ---------------------------------------------------------------------------


def _print_table(rows: list[dict], columns: Optional[list[str]] = None) -> None:
    """Render a list of dicts as a fixed-width ASCII table."""
    if not rows:
        print("  (no rows)")
        return

    cols = columns or list(rows[0].keys())
    widths = {col: len(col) for col in cols}
    for row in rows:
        for col in cols:
            widths[col] = max(widths[col], len(str(row.get(col, ""))))

    sep = "+" + "+".join("-" * (widths[c] + 2) for c in cols) + "+"
    header_row = "|" + "|".join(
        f" {_c('bold', col.upper()):{widths[col]+8}} " for col in cols
    ) + "|"

    print(sep)
    print(header_row)
    print(sep)
    for row in rows:
        line = "|" + "|".join(
            f" {str(row.get(col, '')):{widths[col]}} " for col in cols
        ) + "|"
        print(line)
    print(sep)


def _print_kv(data: dict, indent: int = 0) -> None:
    """Pretty-print a dict as key: value pairs."""
    pad = " " * indent
    for key, val in data.items():
        if isinstance(val, dict):
            print(f"{pad}{_c('cyan', key)}:")
            _print_kv(val, indent + 2)
        elif isinstance(val, list) and val and isinstance(val[0], dict):
            print(f"{pad}{_c('cyan', key)}: [{len(val)} item(s)]")
        else:
            print(f"{pad}{_c('cyan', key)}: {val}")


def _ts_to_str(ts: Optional[int]) -> str:
    if ts is None:
        return "—"
    import datetime
    return datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S UTC")


# ---------------------------------------------------------------------------
# Command dispatch helpers
# ---------------------------------------------------------------------------


def _run(fn, *args, **kwargs) -> Any:
    """Execute a command function, catch exceptions, print errors."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        print(err(f"Error: {exc}"))
        sys.exit(1)


# ---------------------------------------------------------------------------
# db sub-commands
# ---------------------------------------------------------------------------


def _cmd_db(args: argparse.Namespace) -> None:
    from app.cli.commands import cmd_db_status, cmd_db_migrate, cmd_db_rollback

    if args.db_action == "status":
        result = _run(cmd_db_status)
        print(header("\n  Database Status\n"))
        _print_table(
            result["tables"],
            columns=["table", "exists", "rows"],
        )
        present = result["tables_present"]
        total = result["total_tables_known"]
        print(f"\n  {present}/{total} tracked tables present\n")

    elif args.db_action == "migrate":
        result = _run(cmd_db_migrate)
        print(header("\n  Database Migrations\n"))
        if result["applied"]:
            for r in result["applied"]:
                print(ok(f"  Applied [{r['id']}] {r['name']}  ({r['duration_ms']}ms)"))
        else:
            print(ok(f"  {result['message']}"))

    elif args.db_action == "rollback":
        if not args.target:
            print(err("  rollback requires a TARGET migration id"))
            sys.exit(1)
        result = _run(cmd_db_rollback, args.target)
        print(header("\n  Rollback\n"))
        for r in result["rolled_back"]:
            print(warn(f"  Rolled back [{r['id']}] {r['name']}"))
        print(f"\n  {result['message']}\n")

    else:
        print(err(f"Unknown db action: {args.db_action}"))
        sys.exit(1)


# ---------------------------------------------------------------------------
# user sub-commands
# ---------------------------------------------------------------------------


def _cmd_user(args: argparse.Namespace) -> None:
    from app.cli.commands import cmd_user_list, cmd_user_info, cmd_user_delete

    if args.user_action == "list":
        result = _run(cmd_user_list, limit=args.limit, offset=args.offset)
        print(header(f"\n  Users (showing {args.offset + 1} – {args.offset + len(result['users'])} of {result['total']})\n"))
        rows = []
        for u in result["users"]:
            rows.append({
                "pubkey": u["pubkey"][:16] + "...",
                "auth_method": u["auth_method"],
                "created_at": _ts_to_str(u["created_at"]),
            })
        _print_table(rows)
        if result["has_more"]:
            print(warn(f"  More results available. Use --offset {args.offset + args.limit}"))
        print()

    elif args.user_action == "info":
        if not args.pubkey:
            print(err("  'user info' requires PUBKEY argument"))
            sys.exit(1)
        result = _run(cmd_user_info, args.pubkey)
        if not result["found"]:
            print(warn(f"  User {args.pubkey!r} not found"))
        else:
            print(header(f"\n  User: {result['pubkey'][:32]}...\n"))
            _print_kv({
                "auth_method": result["auth_method"],
                "created_at": _ts_to_str(result["created_at"]),
                "deposits": result["deposit_count"],
                "achievements": result["achievement_count"],
                "savings_goal": result.get("savings_goal"),
                "preferences": result.get("preferences"),
            })
        print()

    elif args.user_action == "delete":
        if not args.pubkey:
            print(err("  'user delete' requires PUBKEY argument"))
            sys.exit(1)
        # Safety prompt
        if not args.yes:
            confirm = input(f"  {warn('Delete user')} {args.pubkey[:16]}...? [y/N] ")
            if confirm.strip().lower() != "y":
                print("  Aborted.")
                return
        result = _run(cmd_user_delete, args.pubkey)
        if result["deleted"]:
            print(ok(f"  Deleted user {args.pubkey[:16]}... and related data"))
            _print_kv({"cascaded_deletes": result["cascaded"]})
        else:
            print(warn("  User not found — nothing deleted"))
        print()

    else:
        print(err(f"Unknown user action: {args.user_action}"))
        sys.exit(1)


# ---------------------------------------------------------------------------
# session sub-commands
# ---------------------------------------------------------------------------


def _cmd_session(args: argparse.Namespace) -> None:
    from app.cli.commands import cmd_session_list, cmd_session_cleanup

    if args.session_action == "list":
        result = _run(cmd_session_list)
        print(header(f"\n  Active Sessions ({result['count']})\n"))
        if result["sessions"]:
            _print_table(result["sessions"], columns=["token_prefix", "pubkey", "ttl_seconds"])
        else:
            print("  No active sessions")
        print()

    elif args.session_action == "cleanup":
        result = _run(cmd_session_cleanup)
        print(ok(f"  {result['message']}  ({result['remaining']} remaining)\n"))

    else:
        print(err(f"Unknown session action: {args.session_action}"))
        sys.exit(1)


# ---------------------------------------------------------------------------
# stats sub-commands
# ---------------------------------------------------------------------------


def _cmd_stats(args: argparse.Namespace) -> None:
    from app.cli.commands import cmd_achievement_stats, cmd_savings_stats

    if args.stats_action == "achievements":
        result = _run(cmd_achievement_stats)
        print(header(f"\n  Achievement Distribution\n"))
        print(f"  Total awards: {result['total_awards']}  |  Users: {result['total_users']}  |  Distinct: {result['distinct_achievements']}\n")
        _print_table(result["distribution"])
        print()

    elif args.stats_action == "savings":
        result = _run(cmd_savings_stats)
        print(header("\n  Savings Statistics\n"))
        _print_kv(result)
        print()

    else:
        print(err(f"Unknown stats action: {args.stats_action}"))
        sys.exit(1)


# ---------------------------------------------------------------------------
# price sub-commands
# ---------------------------------------------------------------------------


def _cmd_price(args: argparse.Namespace) -> None:
    from app.cli.commands import cmd_price_check
    result = _run(cmd_price_check)
    print(header("\n  BTC Price Check\n"))
    for src in result["sources"]:
        status = ok(f"  {src['source']}: ${src['price_usd']:,.2f}") if src["ok"] else err(f"  {src['source']}: unavailable")
        print(status)
    if result["median_price_usd"]:
        print(_c("bold", f"\n  Median: ${result['median_price_usd']:,.2f}"))
    print()


# ---------------------------------------------------------------------------
# alerts
# ---------------------------------------------------------------------------


def _cmd_alerts(args: argparse.Namespace) -> None:
    from app.cli.commands import cmd_alert_history
    result = _run(cmd_alert_history, limit=args.limit)
    print(header(f"\n  Recent Events ({result['count']})\n"))
    if result.get("message"):
        print(warn(f"  {result['message']}"))
    elif result["events"]:
        rows = []
        for e in result["events"]:
            rows.append({
                "id": e["id"],
                "pubkey": (e["pubkey"] or "—")[:12] + "...",
                "event_type": e["event_type"],
                "created_at": _ts_to_str(e["created_at"]),
            })
        _print_table(rows)
    print()


# ---------------------------------------------------------------------------
# health check
# ---------------------------------------------------------------------------


def _cmd_health(args: argparse.Namespace) -> None:
    from app.cli.commands import cmd_health_check
    result = _run(cmd_health_check)
    status_str = ok("HEALTHY") if result["healthy"] else err("UNHEALTHY")
    print(header(f"\n  System Health — {status_str}\n"))
    for name, check in result["checks"].items():
        symbol = ok(name) if check.get("ok") else err(name)
        detail = check.get("message") or ""
        if check.get("price_usd"):
            detail = f"${check['price_usd']:,.2f}"
        elif check.get("active") is not None:
            detail = f"{check['active']} active"
        elif check.get("applied") is not None:
            detail = f"{check['applied']} applied, {check['pending']} pending"
        print(f"  {symbol}: {detail}")
    print()


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


def _cmd_export(args: argparse.Namespace) -> None:
    from app.cli.commands import cmd_export_users
    if args.export_type == "users":
        result = _run(cmd_export_users, fmt=args.format, output=args.output)
        if args.output:
            print(ok(f"  Exported {result['row_count']} users to {result['output_path']}"))
        else:
            print(result["data"])
    else:
        print(err(f"Unknown export type: {args.export_type}"))
        sys.exit(1)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="magma-admin",
        description="Magma admin CLI — manage the Magma Bitcoin app",
    )
    parser.add_argument(
        "--version", action="version", version="magma-admin 1.0.0"
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ---- db ----
    db_p = sub.add_parser("db", help="Database management commands")
    db_sub = db_p.add_subparsers(dest="db_action", metavar="ACTION")
    db_sub.required = True
    db_sub.add_parser("status", help="Show table row counts and presence")
    db_sub.add_parser("migrate", help="Apply all pending migrations")
    rollback_p = db_sub.add_parser("rollback", help="Roll back to a migration")
    rollback_p.add_argument("target", metavar="TARGET", help="Migration ID to roll back to")

    # ---- user ----
    user_p = sub.add_parser("user", help="User management commands")
    user_sub = user_p.add_subparsers(dest="user_action", metavar="ACTION")
    user_sub.required = True

    list_p = user_sub.add_parser("list", help="List users with pagination")
    list_p.add_argument("--limit", type=int, default=20, metavar="N")
    list_p.add_argument("--offset", type=int, default=0, metavar="N")

    info_p = user_sub.add_parser("info", help="Detailed info for a single user")
    info_p.add_argument("pubkey", metavar="PUBKEY")

    del_p = user_sub.add_parser("delete", help="Delete a user and all their data")
    del_p.add_argument("pubkey", metavar="PUBKEY")
    del_p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")

    # ---- session ----
    sess_p = sub.add_parser("session", help="Session management commands")
    sess_sub = sess_p.add_subparsers(dest="session_action", metavar="ACTION")
    sess_sub.required = True
    sess_sub.add_parser("list", help="List active sessions")
    sess_sub.add_parser("cleanup", help="Force cleanup of expired sessions")

    # ---- stats ----
    stats_p = sub.add_parser("stats", help="Aggregate statistics")
    stats_sub = stats_p.add_subparsers(dest="stats_action", metavar="ACTION")
    stats_sub.required = True
    stats_sub.add_parser("achievements", help="Achievement distribution")
    stats_sub.add_parser("savings", help="Savings statistics")

    # ---- price ----
    price_p = sub.add_parser("price", help="BTC price commands")
    price_sub = price_p.add_subparsers(dest="price_action", metavar="ACTION")
    price_sub.required = True
    price_sub.add_parser("check", help="Check BTC price from all sources")

    # ---- alerts ----
    alerts_p = sub.add_parser("alerts", help="Show recent alert events")
    alerts_p.add_argument("--limit", type=int, default=50, metavar="N")

    # ---- health ----
    sub.add_parser("health", help="System health check")

    # ---- export ----
    exp_p = sub.add_parser("export", help="Export data")
    exp_sub = exp_p.add_subparsers(dest="export_type", metavar="TYPE")
    exp_sub.required = True
    exp_users_p = exp_sub.add_parser("users", help="Export all users")
    exp_users_p.add_argument(
        "--format", choices=["json", "csv"], default="json", metavar="FMT"
    )
    exp_users_p.add_argument(
        "--output", "-o", metavar="FILE", default=None,
        help="Write output to FILE instead of stdout"
    )

    return parser


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> None:
    """Parse arguments and dispatch to the appropriate handler."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Ensure the config / env is loaded before any command runs
    try:
        from app.config import settings  # noqa: F401
    except Exception:
        pass  # config may not be available in test environments

    dispatch = {
        "db": _cmd_db,
        "user": _cmd_user,
        "session": _cmd_session,
        "stats": _cmd_stats,
        "price": _cmd_price,
        "alerts": _cmd_alerts,
        "health": _cmd_health,
        "export": _cmd_export,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        print(err(f"Unknown command: {args.command}"))
        sys.exit(1)

    handler(args)


if __name__ == "__main__":
    main()
