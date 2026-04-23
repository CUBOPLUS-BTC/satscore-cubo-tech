"""Bitcoin transaction analysis utilities.

Provides confirmation time estimation, RBF/CPFP fee-bump calculations,
transaction efficiency analysis, batch savings, and transaction classification.

All functions are pure-Python with no external dependencies or DB calls.
"""

import math
from .fees import estimate_tx_size, estimate_tx_fee, _DEFAULT_ADDR_TYPE

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BLOCKS_PER_HOUR = 6
_AVG_BLOCK_INTERVAL_MINUTES = 10

# Typical mempool size thresholds (in virtual bytes)
_MEMPOOL_NORMAL = 1_000_000       # ~1 MB — normal
_MEMPOOL_ELEVATED = 5_000_000     # ~5 MB — elevated
_MEMPOOL_CONGESTED = 20_000_000   # ~20 MB — congested


# ---------------------------------------------------------------------------
# Confirmation time estimation
# ---------------------------------------------------------------------------


def estimate_confirmation_time(fee_rate: int, mempool_size: int = 0) -> dict:
    """Estimate how many blocks and minutes until a transaction confirms.

    Uses a heuristic model based on fee_rate tiers and mempool pressure.

    Parameters
    ----------
    fee_rate:
        Transaction fee rate in sat/vB.
    mempool_size:
        Current mempool size in virtual bytes (0 = assume normal).

    Returns
    -------
    dict with keys:
        fee_rate_svb (int), mempool_size_bytes (int),
        mempool_status (str), est_blocks (int),
        est_minutes (int), est_hours (float),
        confidence (str), next_block_likely (bool)
    """
    if mempool_size <= 0:
        mempool_status = "normal"
        pressure = 1.0
    elif mempool_size < _MEMPOOL_NORMAL:
        mempool_status = "clear"
        pressure = 0.8
    elif mempool_size < _MEMPOOL_ELEVATED:
        mempool_status = "normal"
        pressure = 1.0
    elif mempool_size < _MEMPOOL_CONGESTED:
        mempool_status = "elevated"
        pressure = 2.0
    else:
        mempool_status = "congested"
        pressure = 4.0

    # Base blocks by fee rate tier (before pressure adjustment)
    if fee_rate >= 100:
        base_blocks = 1
    elif fee_rate >= 50:
        base_blocks = 1
    elif fee_rate >= 20:
        base_blocks = 2
    elif fee_rate >= 10:
        base_blocks = 3
    elif fee_rate >= 5:
        base_blocks = 6
    elif fee_rate >= 2:
        base_blocks = 12
    else:
        base_blocks = 144

    est_blocks = max(1, int(math.ceil(base_blocks * pressure)))
    est_minutes = est_blocks * _AVG_BLOCK_INTERVAL_MINUTES
    est_hours = round(est_minutes / 60, 1)

    if est_blocks == 1:
        confidence = "high"
    elif est_blocks <= 3:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "fee_rate_svb": fee_rate,
        "mempool_size_bytes": mempool_size,
        "mempool_status": mempool_status,
        "est_blocks": est_blocks,
        "est_minutes": est_minutes,
        "est_hours": est_hours,
        "confidence": confidence,
        "next_block_likely": est_blocks == 1,
    }


# ---------------------------------------------------------------------------
# Transaction efficiency analysis
# ---------------------------------------------------------------------------


def analyze_tx_efficiency(tx_data: dict) -> dict:
    """Analyse the efficiency of a transaction.

    Parameters
    ----------
    tx_data:
        Dict with keys:
          input_count (int), output_count (int),
          total_input_sats (int), total_output_sats (int),
          fee_sats (int), address_type (str, optional)

    Returns
    -------
    dict with keys:
        input_count, output_count, total_input_sats,
        total_output_sats, fee_sats, implied_fee_rate,
        estimated_vbytes, fee_efficiency_pct,
        change_output_likely (bool), input_output_ratio,
        classification (str), recommendations (list[str])
    """
    inputs = int(tx_data.get("input_count", 1))
    outputs = int(tx_data.get("output_count", 2))
    total_in = int(tx_data.get("total_input_sats", 0))
    total_out = int(tx_data.get("total_output_sats", 0))
    fee_sats = int(tx_data.get("fee_sats", 0))
    addr_type = tx_data.get("address_type", _DEFAULT_ADDR_TYPE)

    est_size = estimate_tx_size(inputs, outputs, addr_type)
    vbytes = est_size["vbytes"]
    implied_rate = math.ceil(fee_sats / vbytes) if vbytes > 0 else 0

    fee_efficiency_pct = (
        round(fee_sats / total_in * 100, 4) if total_in > 0 else 0.0
    )

    # Heuristic: change output exists if outputs >= 2
    change_likely = outputs >= 2

    io_ratio = round(inputs / outputs, 2) if outputs > 0 else 0.0

    # Recommendations
    recs = []
    if implied_rate > 50:
        recs.append(f"Fee rate is high ({implied_rate} sat/vB). Consider using RBF and setting a lower initial rate.")
    if inputs > 5:
        recs.append(f"{inputs} inputs detected. Consider pre-consolidating UTXOs during low-fee periods.")
    if outputs > 5:
        recs.append(f"{outputs} outputs. Transaction batching is already in use — good practice.")
    if fee_efficiency_pct > 1.0:
        recs.append(f"Fee is {fee_efficiency_pct:.2f}% of inputs. Consider timing the transaction for lower mempool.")
    if not recs:
        recs.append("Transaction looks efficient.")

    return {
        "input_count": inputs,
        "output_count": outputs,
        "total_input_sats": total_in,
        "total_output_sats": total_out,
        "fee_sats": fee_sats,
        "implied_fee_rate": implied_rate,
        "estimated_vbytes": vbytes,
        "fee_efficiency_pct": fee_efficiency_pct,
        "change_output_likely": change_likely,
        "input_output_ratio": io_ratio,
        "recommendations": recs,
    }


# ---------------------------------------------------------------------------
# RBF (Replace-By-Fee) fee bump
# ---------------------------------------------------------------------------


def calculate_rbf_fee(
    original_fee: int,
    original_vbytes: int,
    target_blocks: int = 1,
    current_fee_rate: int = 30,
) -> dict:
    """Calculate the minimum fee needed to RBF-bump a stuck transaction.

    BIP 125 requires the replacement fee to be at least:
      original_fee + min_relay_fee (typically 1 sat/vB * vbytes)

    Parameters
    ----------
    original_fee:
        Original transaction fee in satoshis.
    original_vbytes:
        Original transaction size in vbytes.
    target_blocks:
        Target confirmation window (default next block).
    current_fee_rate:
        Current market fee rate for the target_blocks window (sat/vB).

    Returns
    -------
    dict with keys:
        original_fee_sats, original_fee_rate,
        target_fee_rate, minimum_replacement_fee,
        recommended_replacement_fee, fee_increase_sats,
        fee_increase_pct, viable (bool)
    """
    original_rate = math.ceil(original_fee / original_vbytes) if original_vbytes > 0 else 1

    # BIP 125 minimum: original_fee + 1 sat/vB * vbytes (min relay)
    bip125_minimum = original_fee + original_vbytes  # 1 sat/vB bump

    # Market-rate fee for target confirmation
    market_fee = current_fee_rate * original_vbytes

    # Take the higher of BIP 125 minimum and market rate
    recommended_fee = max(bip125_minimum, market_fee)

    # Add 10% buffer to ensure the replacement propagates
    recommended_fee = int(math.ceil(recommended_fee * 1.1))

    increase_sats = recommended_fee - original_fee
    increase_pct = (increase_sats / original_fee * 100) if original_fee > 0 else 0.0

    viable = original_rate < current_fee_rate

    return {
        "original_fee_sats": original_fee,
        "original_fee_rate": original_rate,
        "original_vbytes": original_vbytes,
        "target_blocks": target_blocks,
        "target_fee_rate": current_fee_rate,
        "bip125_minimum_fee": bip125_minimum,
        "minimum_replacement_fee": bip125_minimum,
        "recommended_replacement_fee": recommended_fee,
        "fee_increase_sats": increase_sats,
        "fee_increase_pct": round(increase_pct, 1),
        "viable": viable,
        "note": (
            "Transaction can be replaced (RBF)." if viable
            else "Original fee rate already meets or exceeds target. No RBF needed."
        ),
    }


# ---------------------------------------------------------------------------
# CPFP (Child-Pays-For-Parent) fee calculation
# ---------------------------------------------------------------------------


def calculate_cpfp_fee(
    parent_fee: int,
    parent_size: int,
    child_size: int,
    target_fee_rate: int,
) -> dict:
    """Calculate the child transaction fee needed for CPFP.

    The combined package fee rate must meet the target:

        (parent_fee + child_fee) / (parent_size + child_size) >= target_rate

    Parameters
    ----------
    parent_fee:
        Fee paid by the parent (stuck) transaction in satoshis.
    parent_size:
        Size of the parent transaction in vbytes.
    child_size:
        Size of the planned child transaction in vbytes.
    target_fee_rate:
        Desired package fee rate in sat/vB.

    Returns
    -------
    dict with keys:
        parent_fee_sats, parent_size_vb, parent_fee_rate,
        child_size_vb, child_fee_sats, child_fee_rate,
        package_fee_sats, package_size_vb, package_fee_rate,
        target_fee_rate, achieves_target (bool)
    """
    total_package_size = parent_size + child_size
    total_required_fee = target_fee_rate * total_package_size
    child_fee = max(0, total_required_fee - parent_fee)

    # Add 1 sat/vB buffer for child to ensure acceptance
    child_fee = max(child_fee, child_size * 1)

    package_fee = parent_fee + child_fee
    package_rate = package_fee / total_package_size if total_package_size > 0 else 0.0
    parent_rate = parent_fee / parent_size if parent_size > 0 else 0.0
    child_rate = child_fee / child_size if child_size > 0 else 0.0
    achieves = package_rate >= target_fee_rate

    return {
        "parent_fee_sats": parent_fee,
        "parent_size_vb": parent_size,
        "parent_fee_rate": round(parent_rate, 1),
        "child_size_vb": child_size,
        "child_fee_sats": int(math.ceil(child_fee)),
        "child_fee_rate": round(child_rate, 1),
        "package_fee_sats": int(math.ceil(package_fee)),
        "package_size_vb": total_package_size,
        "package_fee_rate": round(package_rate, 2),
        "target_fee_rate": target_fee_rate,
        "achieves_target": achieves,
    }


# ---------------------------------------------------------------------------
# Batch savings
# ---------------------------------------------------------------------------


def estimate_batch_savings(
    recipients: int,
    fee_rate: int,
    address_type: str = _DEFAULT_ADDR_TYPE,
) -> dict:
    """Estimate the fee savings from sending to all recipients in one batch.

    Parameters
    ----------
    recipients:
        Number of payment recipients.
    fee_rate:
        Current fee rate in sat/vB.
    address_type:
        Input/output address type.

    Returns
    -------
    dict with keys:
        recipients, fee_rate_svb, separate_txs_fee_sats,
        batched_tx_fee_sats, savings_sats, savings_pct,
        separate_vbytes_total, batched_vbytes
    """
    if recipients < 2:
        sep_size = estimate_tx_size(1, 2, address_type)["vbytes"]
        sep_fee = sep_size * fee_rate
        return {
            "recipients": recipients,
            "fee_rate_svb": fee_rate,
            "separate_txs_fee_sats": sep_fee,
            "batched_tx_fee_sats": sep_fee,
            "savings_sats": 0,
            "savings_pct": 0.0,
            "separate_vbytes_total": sep_size,
            "batched_vbytes": sep_size,
        }

    # N separate txs: each 1 input, 2 outputs
    sep_vb_each = estimate_tx_size(1, 2, address_type)["vbytes"]
    sep_total_vb = sep_vb_each * recipients
    sep_fee = sep_total_vb * fee_rate

    # 1 batched tx: 1 input, recipients+1 outputs (+ change)
    batch_vb = estimate_tx_size(1, recipients + 1, address_type)["vbytes"]
    batch_fee = batch_vb * fee_rate

    savings = sep_fee - batch_fee
    savings_pct = round(savings / sep_fee * 100, 1) if sep_fee > 0 else 0.0

    return {
        "recipients": recipients,
        "fee_rate_svb": fee_rate,
        "separate_txs_fee_sats": sep_fee,
        "batched_tx_fee_sats": batch_fee,
        "savings_sats": savings,
        "savings_pct": savings_pct,
        "separate_vbytes_total": sep_total_vb,
        "batched_vbytes": batch_vb,
    }


# ---------------------------------------------------------------------------
# Transaction classification
# ---------------------------------------------------------------------------

def classify_transaction(tx_data: dict) -> dict:
    """Classify a transaction by its likely economic purpose.

    Uses heuristics on input/output counts, relative amounts, and
    presence of equal-value outputs to infer the transaction type.

    Parameters
    ----------
    tx_data:
        Dict with keys (all optional):
          input_count (int), output_count (int),
          input_values (list[int] sats), output_values (list[int] sats),
          fee_sats (int)

    Returns
    -------
    dict with keys:
        classification (str), confidence (str),
        description (str), signals (list[str])
    """
    inputs = int(tx_data.get("input_count", 1))
    outputs = int(tx_data.get("output_count", 2))
    in_vals: list[int] = tx_data.get("input_values", [])
    out_vals: list[int] = tx_data.get("output_values", [])
    fee = int(tx_data.get("fee_sats", 0))

    signals = []
    classification = "unknown"
    confidence = "low"
    description = "Insufficient data to classify."

    # --- Consolidation ---
    if inputs > 3 and outputs == 1:
        classification = "consolidation"
        confidence = "high"
        description = "Multiple inputs spent to a single output — UTXO consolidation."
        signals.append(f"{inputs} inputs → 1 output")

    # --- Payment with change ---
    elif inputs >= 1 and outputs == 2:
        classification = "simple_payment"
        confidence = "medium"
        description = "One or more inputs, two outputs — typical payment with change."
        signals.append("2 outputs (recipient + change)")

        # Refine: if one output is much smaller, it might be the change
        if len(out_vals) == 2:
            small = min(out_vals)
            large = max(out_vals)
            if large > small * 10:
                signals.append(f"Large output ({large} sats) likely the payment amount")
                signals.append(f"Small output ({small} sats) likely change")

    # --- Batched payment ---
    elif inputs >= 1 and outputs >= 3:
        # Check for equal-value outputs (CoinJoin signal)
        if len(out_vals) >= 3:
            unique_vals = set(out_vals)
            if len(unique_vals) <= len(out_vals) // 2:
                classification = "coinjoin_or_batch"
                confidence = "medium"
                description = "Multiple outputs with repeated values — possible CoinJoin or batched payment."
                signals.append("Many equal-value outputs detected")
            else:
                classification = "batched_payment"
                confidence = "medium"
                description = f"Single input, {outputs} outputs — batched payment to multiple recipients."
                signals.append(f"{outputs} distinct-value outputs")
        else:
            classification = "batched_payment"
            confidence = "low"
            description = f"{outputs} outputs — likely a batched payment."

    # --- Sweep ---
    elif inputs >= 1 and outputs == 1:
        classification = "sweep"
        confidence = "medium"
        description = "All funds swept to a single output — wallet sweep or consolidation."
        signals.append("Single output, no change")

    # --- Coinbase (no inputs) ---
    elif inputs == 0:
        classification = "coinbase"
        confidence = "high"
        description = "No inputs — coinbase transaction (block reward)."
        signals.append("Zero inputs")

    # Fee anomaly check
    if fee > 0 and in_vals:
        total_in = sum(in_vals)
        if total_in > 0 and fee / total_in > 0.05:
            signals.append(f"High fee: {fee} sats ({fee/total_in*100:.1f}% of inputs)")

    return {
        "classification": classification,
        "confidence": confidence,
        "description": description,
        "signals": signals,
        "input_count": inputs,
        "output_count": outputs,
    }
