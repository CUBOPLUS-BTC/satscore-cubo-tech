"""Bitcoin address analyzer — computes multi-dimensional scores from on-chain data."""

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..services.mempool_client import MempoolClient

# Weights that sum to 1000 for total_score
_W_ACTIVITY = 0.30   # 300 pts max
_W_HODL = 0.35       # 350 pts max
_W_DIVERSITY = 0.35  # 350 pts max

# Satoshi precision
_SATS_PER_BTC = 100_000_000

# Thresholds for grade assignment
_GRADE_THRESHOLDS = [
    (900, "A+"),
    (800, "A"),
    (700, "B+"),
    (600, "B"),
    (500, "C+"),
    (400, "C"),
    (300, "D"),
    (0,   "F"),
]

# How many days a UTXO must be unspent to be considered "well-held"
_HODL_BASELINE_DAYS = 365

# Regex patterns for Bitcoin address formats
_RE_BECH32    = re.compile(r"^bc1[ac-hj-np-z02-9]{6,87}$")
_RE_P2PKH     = re.compile(r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$")
_RE_BECH32M   = re.compile(r"^bc1p[ac-hj-np-z02-9]{58}$")   # Taproot


def validate_bitcoin_address(address: str) -> bool:
    """Return True if address matches a known Bitcoin mainnet format.

    Supported formats:
      - Legacy P2PKH / P2SH  (starts with 1 or 3)
      - Native SegWit P2WPKH / P2WSH  (bc1q…)
      - Taproot P2TR  (bc1p…)
    """
    if not isinstance(address, str) or not address:
        return False
    addr = address.strip()
    return bool(
        _RE_BECH32m.match(addr)
        or _RE_BECH32.match(addr)
        or _RE_P2PKH.match(addr)
    )


# Alias used internally — avoids shadowing the public function name below.
_RE_BECH32m = _RE_BECH32M


class AddressAnalyzer:
    """Fetches live on-chain data and produces a comprehensive score for a
    Bitcoin address.  All heavy I/O is done concurrently; scoring math is
    deterministic and documented in-line.
    """

    def __init__(self, mempool_client: MempoolClient | None = None):
        self._client = mempool_client or MempoolClient()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, address: str) -> dict:
        """Fetch data from mempool.space and return a full analysis dict.

        Raises ValueError for invalid addresses.
        Raises RuntimeError when the API is unreachable.
        """
        address = address.strip()
        if not validate_bitcoin_address(address):
            raise ValueError(f"Invalid Bitcoin address: {address!r}")

        info, txs, utxos = self._fetch_all(address)

        chain = info.get("chain_stats", {})
        mempool = info.get("mempool_stats", {})

        total_received = chain.get("funded_txo_sum", 0)          # sats
        total_spent    = chain.get("spent_txo_sum", 0)            # sats
        balance        = total_received - total_spent              # sats

        # Combine confirmed + unconfirmed tx counts
        tx_count = (
            chain.get("tx_count", 0) + mempool.get("tx_count", 0)
        )
        utxo_count = len(utxos)

        first_seen, last_active = self._extract_timestamps(txs)
        activity_score = self._compute_activity_score(tx_count, first_seen, last_active)
        hodl_score     = self._compute_hodl_score(utxos, balance)
        diversity_score= self._compute_diversity_score(utxos, balance)

        raw_total  = (
            activity_score  * _W_ACTIVITY * 1000
            + hodl_score    * _W_HODL     * 1000
            + diversity_score * _W_DIVERSITY * 1000
        )
        total_score = round(min(1000, max(0, raw_total)))
        grade       = self._assign_grade(total_score)
        recommendations = self._build_recommendations(
            total_score, activity_score, hodl_score, diversity_score,
            balance, utxo_count, tx_count
        )

        return {
            "address": address,
            "total_received":   total_received,
            "total_sent":       total_spent,
            "balance":          balance,
            "balance_btc":      round(balance / _SATS_PER_BTC, 8),
            "tx_count":         tx_count,
            "utxo_count":       utxo_count,
            "first_seen":       first_seen,
            "last_active":      last_active,
            "activity_score":   round(activity_score * 100),
            "hodl_score":       round(hodl_score * 100),
            "diversity_score":  round(diversity_score * 100),
            "total_score":      total_score,
            "grade":            grade,
            "recommendations":  recommendations,
            "analyzed_at":      int(time.time()),
        }

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _fetch_all(self, address: str) -> tuple[dict, list, list]:
        """Fetch address info, transactions, and UTXOs concurrently."""
        results = {}
        errors  = {}

        tasks = {
            "info":  self._client.get_address_info,
            "txs":   self._client.get_address_txs,
            "utxos": self._client.get_address_utxos,
        }

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(fn, address): key for key, fn in tasks.items()}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception as exc:
                    errors[key] = exc

        if "info" in errors:
            raise RuntimeError(f"Could not fetch address info: {errors['info']}")

        return (
            results.get("info", {}),
            results.get("txs",  []),
            results.get("utxos", []),
        )

    # ------------------------------------------------------------------
    # Timestamp helpers
    # ------------------------------------------------------------------

    def _extract_timestamps(self, txs: list) -> tuple[int | None, int | None]:
        """Return (first_seen, last_active) as Unix timestamps or None."""
        timestamps = []
        for tx in txs:
            status = tx.get("status", {})
            if status.get("confirmed") and status.get("block_time"):
                timestamps.append(int(status["block_time"]))

        if not timestamps:
            return None, None

        return min(timestamps), max(timestamps)

    # ------------------------------------------------------------------
    # Scoring sub-components  (all return float in [0, 1])
    # ------------------------------------------------------------------

    def _compute_activity_score(
        self,
        tx_count: int,
        first_seen: int | None,
        last_active: int | None,
    ) -> float:
        """Score based on transaction frequency relative to wallet age.

        Logic:
          - A brand-new wallet with zero TXs scores 0.
          - We reward consistent usage: aim for ~2–4 TXs/month as "ideal".
          - Frequency above the ceiling is capped at 1.0 (not penalised).
          - Recency bonus: if last_active within 90 days, add up to 0.15.
        """
        if tx_count == 0 or first_seen is None or last_active is None:
            return 0.0

        now    = time.time()
        age_s  = max(1, last_active - first_seen)
        age_d  = age_s / 86400           # wallet age in days
        age_m  = max(1, age_d / 30.44)  # months

        tx_per_month = tx_count / age_m

        # Sigmoid-like ramp: 0 → 0 at 0 tx/mo, saturates near 1.0 at ~8 tx/mo
        raw_freq = min(1.0, tx_per_month / 8.0)

        # Recency: was the wallet active in the last 90 days?
        days_since_active = (now - last_active) / 86400
        if days_since_active <= 30:
            recency_bonus = 0.15
        elif days_since_active <= 90:
            recency_bonus = 0.08
        else:
            recency_bonus = 0.0

        return min(1.0, raw_freq * 0.85 + recency_bonus)

    def _compute_hodl_score(self, utxos: list, balance: int) -> float:
        """Score based on how long UTXOs have been held unspent.

        A wallet where all UTXOs are older than _HODL_BASELINE_DAYS (365 days)
        scores 1.0.  Fresh UTXOs drag the score down proportionally by their
        weight in the total balance.

        Edge cases:
          - No UTXOs → 0.0 (nothing to score)
          - Zero balance → 0.0
        """
        if not utxos or balance <= 0:
            return 0.0

        now = time.time()
        weighted_age_score = 0.0
        total_value        = 0

        for utxo in utxos:
            value = utxo.get("value", 0)
            if value <= 0:
                continue

            status = utxo.get("status", {})
            if status.get("confirmed") and status.get("block_time"):
                age_days = (now - int(status["block_time"])) / 86400
            else:
                # Unconfirmed UTXOs are treated as 0-day-old
                age_days = 0.0

            # Score per UTXO: ramps from 0 → 1 over _HODL_BASELINE_DAYS
            utxo_score = min(1.0, age_days / _HODL_BASELINE_DAYS)

            # Weight by sats so large UTXOs have proportional influence
            weighted_age_score += utxo_score * value
            total_value        += value

        if total_value == 0:
            return 0.0

        raw_hodl = weighted_age_score / total_value

        # Bonus for multi-year holders (over 2 years)
        long_term_count = sum(
            1 for u in utxos
            if u.get("status", {}).get("confirmed")
            and u.get("status", {}).get("block_time")
            and (now - u["status"]["block_time"]) / 86400 >= 730
        )
        if long_term_count > 0 and long_term_count == len(utxos):
            raw_hodl = min(1.0, raw_hodl + 0.10)

        return raw_hodl

    def _compute_diversity_score(self, utxos: list, balance: int) -> float:
        """Score based on UTXO distribution — penalises concentration.

        Reasoning:
          - A single UTXO holding 100 % of balance → heavy concentration risk
            (coin-join / privacy issues; single point of failure for large TXs).
          - Ideal: multiple UTXOs each holding < 25 % of balance.
          - We use a Herfindahl-Hirschman Index (HHI) normalised to [0, 1].
              HHI = sum(share_i^2); perfect equality → 1/n; monopoly → 1.
              diversity = 1 - normalised_HHI

        Edge cases:
          - Zero UTXOs or zero balance → 0.0
          - Single UTXO → low score but not zero (some partial credit for having BTC).
        """
        if not utxos or balance <= 0:
            return 0.0

        values = [u.get("value", 0) for u in utxos if u.get("value", 0) > 0]
        if not values:
            return 0.0

        n     = len(values)
        total = sum(values)
        if total == 0:
            return 0.0

        # Normalised HHI ∈ [0, 1]: 0 = perfect equality, 1 = monopoly
        hhi        = sum((v / total) ** 2 for v in values)
        hhi_min    = 1.0 / n           # minimum possible HHI for n items
        hhi_norm   = (hhi - hhi_min) / (1.0 - hhi_min) if n > 1 else 1.0

        raw_diversity = 1.0 - hhi_norm

        # Small bonus for having at least 5 UTXOs (good coin control)
        if n >= 5:
            raw_diversity = min(1.0, raw_diversity + 0.05)
        if n >= 10:
            raw_diversity = min(1.0, raw_diversity + 0.05)

        # Penalty if any single UTXO is > 80 % of total balance
        max_share = max(v / total for v in values)
        if max_share > 0.80:
            raw_diversity *= 0.60
        elif max_share > 0.60:
            raw_diversity *= 0.80

        return raw_diversity

    # ------------------------------------------------------------------
    # Grade assignment
    # ------------------------------------------------------------------

    def _assign_grade(self, total_score: int) -> str:
        for threshold, grade in _GRADE_THRESHOLDS:
            if total_score >= threshold:
                return grade
        return "F"

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------

    def _build_recommendations(
        self,
        total_score: int,
        activity_score: float,
        hodl_score: float,
        diversity_score: float,
        balance: int,
        utxo_count: int,
        tx_count: int,
    ) -> list[str]:
        """Return a list of actionable recommendations tailored to the scores."""
        recs = []

        # Activity recommendations
        if activity_score < 0.30:
            if tx_count == 0:
                recs.append(
                    "This address has no confirmed transactions yet. "
                    "Start accumulating sats to build your on-chain history."
                )
            else:
                recs.append(
                    "Transaction frequency is low. "
                    "Consider making regular DCA (dollar-cost averaging) purchases "
                    "to improve your activity score."
                )
        elif activity_score < 0.60:
            recs.append(
                "Good transaction history. Maintaining a consistent purchase cadence "
                "(e.g., weekly or monthly) will push your activity score higher."
            )

        # HODL recommendations
        if hodl_score < 0.25:
            recs.append(
                "Your UTXOs are mostly recent. "
                "Long-term HODLing (holding UTXOs for 1+ year) significantly "
                "strengthens this score — resist the urge to move coins unnecessarily."
            )
        elif hodl_score < 0.60:
            recs.append(
                "Some UTXOs are maturing well. Avoid spending older UTXOs when "
                "possible; let them age to maximise your HODL score."
            )
        elif hodl_score >= 0.85:
            recs.append(
                "Excellent long-term holding discipline. "
                "Your UTXOs demonstrate strong conviction — diamond hands confirmed."
            )

        # Diversity recommendations
        if utxo_count == 0:
            recs.append(
                "No UTXOs found. Fund this address to start tracking coin control metrics."
            )
        elif utxo_count == 1:
            recs.append(
                "Only one UTXO detected. Accumulating multiple smaller UTXOs "
                "improves privacy, fee flexibility, and your diversity score."
            )
        elif diversity_score < 0.40:
            recs.append(
                "UTXO concentration is high — one output dominates the balance. "
                "Use coin control to keep individual UTXOs under 25 % of your total balance."
            )

        # Balance-based tips
        if balance > 0 and balance < 10_000:
            recs.append(
                "Balance is below 10,000 sats. Consider consolidating during "
                "low-fee periods to avoid UTXOs that cost more to spend than they hold."
            )
        elif balance >= 10_000_000:  # 0.1 BTC
            recs.append(
                "Significant balance detected. Ensure you are using a hardware wallet "
                "and have tested your recovery phrase."
            )

        # Overall score tips
        if total_score >= 800:
            recs.append(
                "Outstanding overall score! Your on-chain behaviour reflects "
                "best practices in self-custody, HODLing, and coin management."
            )
        elif total_score < 300 and tx_count > 0:
            recs.append(
                "Your overall score has room to improve. "
                "Focus on consistent accumulation, long-term holding, "
                "and distributing your balance across multiple UTXOs."
            )

        return recs
