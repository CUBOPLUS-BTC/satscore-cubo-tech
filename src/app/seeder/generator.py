"""
Realistic test-data generation for the Magma Bitcoin application.

All data is deterministically reproducible when a fixed ``seed`` is used,
making it safe for test suites.  No third-party libraries required.
"""

import hashlib
import json
import math
import random
import string
import time
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ACHIEVEMENT_TYPES = [
    "first_deposit", "streak_7", "streak_30", "streak_90",
    "goal_reached", "sats_1k", "sats_10k", "sats_100k", "sats_1m",
    "btc_01", "btc_1", "early_adopter", "hodler", "diamond_hands",
    "lightning_payment", "referral", "anniversary_1y", "anniversary_2y",
]

EVENT_TYPES = [
    "page_view", "deposit", "withdrawal", "goal_update", "login",
    "price_alert_triggered", "achievement_unlocked", "settings_changed",
    "export_generated", "webhook_created",
]

COUNTRY_CODES = [
    "SV", "US", "MX", "GT", "HN", "NI", "CR", "PA",
    "CO", "VE", "EC", "PE", "BR", "AR", "CL", "BO",
    "PY", "UY", "DO", "PR",
]

CURRENCIES = ["USD", "BTC", "SAT"]


# ---------------------------------------------------------------------------
# DataGenerator
# ---------------------------------------------------------------------------

class DataGenerator:
    """
    Generates realistic fake data for seeding the Magma application.

    Args:
        seed: Optional RNG seed for reproducible output.

    Example::

        gen = DataGenerator(seed=42)
        users = gen.generate_pubkeys(50)
        prices = gen.generate_price_history(365, start_price=30000, volatility=0.03)
    """

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)
        self._seed = seed

    # ------------------------------------------------------------------
    # Identity / address generation
    # ------------------------------------------------------------------

    def generate_pubkey(self) -> str:
        """Generate a random 64-character hex string (Nostr public key format)."""
        return "".join(
            self._rng.choice("0123456789abcdef") for _ in range(64)
        )

    def generate_pubkeys(self, count: int) -> List[str]:
        """Generate a list of unique random pubkeys."""
        keys = set()
        while len(keys) < count:
            keys.add(self.generate_pubkey())
        return list(keys)

    def generate_bitcoin_address(self, addr_type: str = "p2wpkh") -> str:
        """
        Generate a plausible (but not cryptographically valid) Bitcoin address.

        Args:
            addr_type: ``"p2pkh"``, ``"p2sh"``, or ``"p2wpkh"``.

        Returns:
            Address string.
        """
        charset = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        if addr_type == "p2pkh":
            body = "".join(self._rng.choice(charset) for _ in range(33))
            return f"1{body}"
        elif addr_type == "p2sh":
            body = "".join(self._rng.choice(charset) for _ in range(33))
            return f"3{body}"
        else:  # p2wpkh (bech32)
            chars = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
            body = "".join(self._rng.choice(chars) for _ in range(39))
            return f"bc1{body}"

    # ------------------------------------------------------------------
    # Price data
    # ------------------------------------------------------------------

    def generate_price_history(
        self,
        days: int = 365,
        start_price: float = 30_000.0,
        volatility: float = 0.03,
    ) -> List[Dict]:
        """
        Generate a realistic BTC price history using geometric Brownian motion.

        Args:
            days:        Number of daily OHLCV bars to generate.
            start_price: Starting price in USD.
            volatility:  Daily volatility (standard deviation of log returns).

        Returns:
            List of OHLCV dicts with ``timestamp``, ``open``, ``high``, ``low``,
            ``close``, ``volume`` keys.
        """
        import datetime
        bars = []
        price = start_price
        now = int(time.time())
        start_ts = now - days * 86400

        for i in range(days):
            # Geometric Brownian Motion step
            drift = 0.0003  # slight upward drift
            shock = self._rng.gauss(0, volatility)
            daily_return = math.exp(drift + shock)
            open_p = price
            close_p = price * daily_return

            intra_vol = abs(self._rng.gauss(0, volatility * 0.5))
            high_p = max(open_p, close_p) * (1 + intra_vol)
            low_p = min(open_p, close_p) * (1 - intra_vol)

            volume = self._rng.uniform(500, 5000) * (price / 50_000)

            ts = start_ts + i * 86400
            bars.append({
                "timestamp": ts,
                "date": datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d"),
                "open": round(open_p, 2),
                "high": round(high_p, 2),
                "low": round(low_p, 2),
                "close": round(close_p, 2),
                "volume": round(volume, 4),
            })
            price = close_p

        return bars

    def generate_realistic_btc_prices(
        self,
        start_date: int,
        end_date: int,
    ) -> List[Dict]:
        """
        Generate BTC prices with realistic patterns: long bear, bull, consolidation phases.

        Args:
            start_date: Unix timestamp of first bar.
            end_date:   Unix timestamp of last bar.

        Returns:
            List of daily price dicts.
        """
        days = max(1, (end_date - start_date) // 86400)
        phases = [
            ("bull", int(days * 0.3), 0.04, 0.0008),
            ("bear", int(days * 0.25), 0.05, -0.0010),
            ("consolidation", int(days * 0.2), 0.015, 0.0001),
            ("bull", int(days * 0.25), 0.035, 0.0006),
        ]

        bars = []
        price = 20_000.0 + self._rng.uniform(-2000, 2000)
        ts = start_date

        for phase_name, phase_days, vol, drift in phases:
            for _ in range(phase_days):
                shock = self._rng.gauss(0, vol)
                price = price * math.exp(drift + shock)
                price = max(100.0, price)
                intra = abs(self._rng.gauss(0, vol * 0.4))
                bars.append({
                    "timestamp": ts,
                    "open": round(price, 2),
                    "high": round(price * (1 + intra), 2),
                    "low": round(price * (1 - intra), 2),
                    "close": round(price, 2),
                    "volume": round(self._rng.uniform(300, 3000), 2),
                    "phase": phase_name,
                })
                ts += 86400
                if ts > end_date:
                    break
            if ts > end_date:
                break

        return bars

    # ------------------------------------------------------------------
    # User activity data
    # ------------------------------------------------------------------

    def generate_deposits(
        self,
        pubkey: str,
        count: int = 20,
        date_range: Optional[Tuple[int, int]] = None,
    ) -> List[Dict]:
        """
        Generate plausible deposit records for a user.

        Args:
            pubkey:     User public key.
            count:      Number of deposit records.
            date_range: ``(start_ts, end_ts)`` tuple; defaults to last 365 days.

        Returns:
            List of deposit dicts.
        """
        now = int(time.time())
        if date_range is None:
            date_range = (now - 365 * 86400, now)
        start, end = date_range

        deposits = []
        for _ in range(count):
            ts = self._rng.randint(start, end)
            sats = self._rng.choice([
                self._rng.randint(10_000, 100_000),
                self._rng.randint(100_000, 1_000_000),
                self._rng.randint(1_000_000, 10_000_000),
            ])
            deposits.append({
                "pubkey": pubkey,
                "amount_sats": sats,
                "tx_hash": self.generate_pubkey(),
                "created_at": ts,
                "confirmed": self._rng.random() > 0.05,
                "note": self._rng.choice([None, "savings", "dca", "lump sum"]),
            })
        return sorted(deposits, key=lambda d: d["created_at"])

    def generate_savings_goal(self, pubkey: str) -> Dict:
        """
        Generate a realistic savings goal for a user.

        Returns:
            Savings goal dict.
        """
        monthly_usd = self._rng.choice([50, 100, 200, 500, 1000, 2500])
        years = self._rng.choice([5, 10, 15, 20, 30])
        return {
            "pubkey": pubkey,
            "monthly_target_usd": monthly_usd,
            "target_years": years,
            "monthly_contribution_usd": monthly_usd * self._rng.uniform(0.8, 1.2),
            "starting_btc_price": self._rng.uniform(20_000, 70_000),
            "created_at": int(time.time()) - self._rng.randint(0, 365 * 86400),
        }

    def generate_achievements(
        self,
        pubkey: str,
        count: int = 5,
    ) -> List[Dict]:
        """
        Generate a set of earned achievements for a user.

        Args:
            pubkey: User public key.
            count:  Number of achievements to award.

        Returns:
            List of achievement dicts.
        """
        chosen = self._rng.sample(
            ACHIEVEMENT_TYPES,
            min(count, len(ACHIEVEMENT_TYPES)),
        )
        now = int(time.time())
        return [
            {
                "pubkey": pubkey,
                "achievement_type": a_type,
                "earned_at": now - self._rng.randint(0, 365 * 86400),
                "metadata": json.dumps({"level": self._rng.randint(1, 5)}),
            }
            for a_type in chosen
        ]

    def generate_transactions(
        self,
        pubkey: str,
        count: int = 30,
    ) -> List[Dict]:
        """
        Generate mixed on-chain and Lightning transaction records.

        Returns:
            List of transaction dicts.
        """
        now = int(time.time())
        txs = []
        for _ in range(count):
            is_lightning = self._rng.random() > 0.4
            direction = self._rng.choice(["in", "out"])
            sats = (
                self._rng.randint(1_000, 500_000)
                if is_lightning
                else self._rng.randint(50_000, 10_000_000)
            )
            txs.append({
                "pubkey": pubkey,
                "tx_id": self.generate_pubkey(),
                "type": "lightning" if is_lightning else "onchain",
                "direction": direction,
                "amount_sats": sats,
                "fee_sats": self._rng.randint(1, max(1, sats // 200)),
                "timestamp": now - self._rng.randint(0, 365 * 86400),
                "confirmed": not is_lightning or self._rng.random() > 0.02,
                "memo": self._rng.choice([None, "DCA", "payment", "savings transfer"]),
            })
        return sorted(txs, key=lambda t: t["timestamp"])

    def generate_webhook_subscription(self, pubkey: str) -> Dict:
        """
        Generate a webhook subscription record.

        Returns:
            Webhook dict.
        """
        events = self._rng.sample(
            ["price_alert", "deposit_confirmed", "achievement_unlocked", "fee_alert"],
            self._rng.randint(1, 4),
        )
        return {
            "pubkey": pubkey,
            "url": f"https://hooks.example.com/{pubkey[:8]}",
            "events": json.dumps(events),
            "secret": "".join(self._rng.choices(string.hexdigits, k=32)).lower(),
            "created_at": int(time.time()) - self._rng.randint(0, 30 * 86400),
            "active": True,
            "delivery_count": self._rng.randint(0, 500),
            "failure_count": self._rng.randint(0, 10),
        }

    def generate_analytics_events(
        self,
        pubkey: str,
        count: int = 50,
    ) -> List[Dict]:
        """
        Generate analytics event records for a user.

        Returns:
            List of event dicts.
        """
        now = int(time.time())
        events = []
        for _ in range(count):
            event_type = self._rng.choice(EVENT_TYPES)
            events.append({
                "pubkey": pubkey,
                "event_type": event_type,
                "timestamp": now - self._rng.randint(0, 90 * 86400),
                "properties": json.dumps({
                    "page": self._rng.choice(["/dashboard", "/savings", "/market", "/settings"]),
                    "duration_ms": self._rng.randint(100, 30_000),
                }),
                "session_id": "".join(self._rng.choices(string.hexdigits, k=16)).lower(),
                "country": self._rng.choice(COUNTRY_CODES),
            })
        return sorted(events, key=lambda e: e["timestamp"])

    def generate_audit_log_entries(self, count: int = 100) -> List[Dict]:
        """
        Generate audit log entries simulating admin/system actions.

        Returns:
            List of audit log dicts.
        """
        actions = [
            "user_login", "user_logout", "settings_update", "goal_created",
            "goal_updated", "webhook_created", "webhook_deleted",
            "admin_login", "config_changed", "export_generated",
        ]
        now = int(time.time())
        entries = []
        for _ in range(count):
            entries.append({
                "actor": self.generate_pubkey(),
                "action": self._rng.choice(actions),
                "target": self._rng.choice([None, self.generate_pubkey()]),
                "ip_address": f"{self._rng.randint(1,254)}.{self._rng.randint(0,254)}.{self._rng.randint(0,254)}.{self._rng.randint(1,254)}",
                "timestamp": now - self._rng.randint(0, 30 * 86400),
                "success": self._rng.random() > 0.03,
                "metadata": json.dumps({}),
            })
        return sorted(entries, key=lambda e: e["timestamp"])

    def generate_trade_history(
        self,
        count: int = 50,
        start_price: float = 40_000.0,
    ) -> List[Dict]:
        """
        Generate a simulated trade history (buy/sell events).

        Returns:
            List of trade dicts.
        """
        now = int(time.time())
        trades = []
        price = start_price
        for i in range(count):
            shock = self._rng.gauss(0, 0.025)
            price = max(1000.0, price * math.exp(shock))
            side = self._rng.choice(["buy", "sell"])
            usd_amount = self._rng.choice([50, 100, 250, 500, 1000, 5000])
            sats = int(usd_amount / price * 1e8)
            trades.append({
                "trade_id": self.generate_pubkey()[:16],
                "side": side,
                "price_usd": round(price, 2),
                "amount_usd": usd_amount,
                "amount_sats": sats,
                "fee_usd": round(usd_amount * 0.005, 4),
                "timestamp": now - (count - i) * self._rng.randint(3600, 86400),
            })
        return trades

    def generate_portfolio(
        self,
        pubkey: str,
        n_assets: int = 3,
    ) -> Dict:
        """
        Generate a portfolio snapshot for a user.

        Returns:
            Portfolio dict with asset allocations.
        """
        asset_names = ["BTC", "USDT", "SATS", "ETH", "SOL"][:n_assets]
        btc_price = self._rng.uniform(20_000, 80_000)
        allocations = []
        total_usd = 0.0
        for asset in asset_names:
            if asset in ("BTC", "SATS"):
                sats = self._rng.randint(100_000, 50_000_000)
                usd = round(sats / 1e8 * btc_price, 2)
            else:
                usd = round(self._rng.uniform(100, 10_000), 2)
                sats = 0
            allocations.append({
                "asset": asset,
                "amount_sats": sats,
                "value_usd": usd,
            })
            total_usd += usd

        for a in allocations:
            a["allocation_pct"] = round(a["value_usd"] / total_usd * 100, 2)

        return {
            "pubkey": pubkey,
            "total_value_usd": round(total_usd, 2),
            "btc_price_usd": round(btc_price, 2),
            "snapshot_at": int(time.time()),
            "assets": allocations,
        }
