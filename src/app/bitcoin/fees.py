"""Bitcoin fee estimation utilities.

All functions are pure-Python with no external dependencies.
Sizes and weights are calculated using the standard vbyte formula:

    vbytes = ceil(weight_units / 4)

where:
    weight_units = base_size * 3 + total_size

References:
  - BIP 141 (SegWit)
  - https://bitcoinops.org/en/tools/calc-fees/
"""

import math
from .address import _INPUT_VBYTES, _OUTPUT_VBYTES

# ---------------------------------------------------------------------------
# Transaction overhead constants (vbytes)
# ---------------------------------------------------------------------------

# Non-witness base overhead per transaction
_TX_OVERHEAD_BASE = 10          # version (4) + locktime (4) + input count (1) + output count (1)
_TX_SEGWIT_MARKER_WEIGHT = 2    # segwit flag bytes count toward weight, not vbytes directly

# Default address type for estimates when not specified
_DEFAULT_ADDR_TYPE = "p2wpkh"


# ---------------------------------------------------------------------------
# Size estimation
# ---------------------------------------------------------------------------


def estimate_tx_size(
    inputs: int,
    outputs: int,
    address_type: str = _DEFAULT_ADDR_TYPE,
) -> dict:
    """Estimate the size of a transaction in vbytes and weight units.

    Parameters
    ----------
    inputs:
        Number of inputs to spend.
    outputs:
        Number of outputs (change + recipients).
    address_type:
        Address type of the inputs being spent.  Output type is assumed
        to match.  Defaults to ``"p2wpkh"``.

    Returns
    -------
    dict with keys:
        vbytes (int), weight_units (int),
        input_vbytes_each (int), output_vbytes_each (int),
        is_segwit (bool), breakdown (dict)
    """
    input_vb = _INPUT_VBYTES.get(address_type, _INPUT_VBYTES[_DEFAULT_ADDR_TYPE])
    output_vb = _OUTPUT_VBYTES.get(address_type, _OUTPUT_VBYTES[_DEFAULT_ADDR_TYPE])
    is_segwit = address_type in ("p2wpkh", "p2wsh", "p2tr")

    total_input_vb = inputs * input_vb
    total_output_vb = outputs * output_vb
    overhead = _TX_OVERHEAD_BASE

    if is_segwit:
        # Weight = (non-witness bytes * 4) + witness bytes
        # Simplified: vbytes ≈ overhead + inputs * input_vb + outputs * output_vb
        # (the witness discount is already baked into _INPUT_VBYTES for segwit types)
        weight_units = (overhead + total_input_vb + total_output_vb) * 4 + _TX_SEGWIT_MARKER_WEIGHT
    else:
        weight_units = (overhead + total_input_vb + total_output_vb) * 4

    vbytes = math.ceil(weight_units / 4)

    return {
        "vbytes": vbytes,
        "weight_units": weight_units,
        "input_vbytes_each": input_vb,
        "output_vbytes_each": output_vb,
        "is_segwit": is_segwit,
        "breakdown": {
            "overhead_vb": overhead,
            "inputs_vb": total_input_vb,
            "outputs_vb": total_output_vb,
        },
    }


# ---------------------------------------------------------------------------
# Fee calculation
# ---------------------------------------------------------------------------


def estimate_tx_fee(
    inputs: int,
    outputs: int,
    fee_rate: int,
    address_type: str = _DEFAULT_ADDR_TYPE,
) -> dict:
    """Estimate the total miner fee for a transaction.

    Parameters
    ----------
    inputs:
        Number of UTXOs being spent.
    outputs:
        Number of outputs created.
    fee_rate:
        Fee rate in satoshis per virtual byte (sat/vB).
    address_type:
        Type of the input addresses.

    Returns
    -------
    dict with keys:
        fee_sats (int), fee_rate_svb (int),
        vbytes (int), weight_units (int),
        fee_usd_at_60k (float), fee_pct_of_1_btc (float)
    """
    size = estimate_tx_size(inputs, outputs, address_type)
    fee_sats = size["vbytes"] * fee_rate

    # Convenience USD estimate at a reference price of $60,000
    fee_usd_ref = fee_sats / 100_000_000 * 60_000

    return {
        "fee_sats": fee_sats,
        "fee_rate_svb": fee_rate,
        "vbytes": size["vbytes"],
        "weight_units": size["weight_units"],
        "fee_usd_at_60k": round(fee_usd_ref, 4),
        "fee_pct_of_1_btc": round(fee_sats / 100_000_000 * 100, 6),
        "size_breakdown": size["breakdown"],
    }


# ---------------------------------------------------------------------------
# Fee as percentage of send amount
# ---------------------------------------------------------------------------


def calculate_fee_savings(
    amount_usd: float,
    fee_rate: int,
    btc_price: float,
    inputs: int = 1,
    outputs: int = 2,
    address_type: str = _DEFAULT_ADDR_TYPE,
) -> dict:
    """Calculate the fee as a percentage of the send amount.

    Parameters
    ----------
    amount_usd:
        Amount being sent in USD.
    fee_rate:
        Fee rate in sat/vB.
    btc_price:
        Current BTC/USD price.
    inputs:
        Number of inputs (default 1).
    outputs:
        Number of outputs including change (default 2).
    address_type:
        Input address type.

    Returns
    -------
    dict with keys:
        amount_usd, fee_sats, fee_usd, fee_pct,
        effective_amount_usd, is_dust_threshold (bool),
        comparison_western_union_usd
    """
    fee_info = estimate_tx_fee(inputs, outputs, fee_rate, address_type)
    fee_sats = fee_info["fee_sats"]
    fee_usd = fee_sats / 100_000_000 * btc_price if btc_price > 0 else 0.0
    fee_pct = (fee_usd / amount_usd * 100) if amount_usd > 0 else 0.0
    effective = amount_usd - fee_usd

    # Western Union approximate fee for comparison
    wu_fee = 4.99 + amount_usd * 0.055
    savings_vs_wu = wu_fee - fee_usd

    # Dust heuristic: fee > 30% of send amount
    is_dust = fee_pct > 30

    return {
        "amount_usd": round(amount_usd, 2),
        "fee_sats": fee_sats,
        "fee_usd": round(fee_usd, 4),
        "fee_pct": round(fee_pct, 4),
        "effective_amount_usd": round(effective, 2),
        "is_dust_threshold": is_dust,
        "comparison_western_union_usd": round(wu_fee, 2),
        "savings_vs_western_union_usd": round(savings_vs_wu, 2),
    }


# ---------------------------------------------------------------------------
# UTXO consolidation advice
# ---------------------------------------------------------------------------


def suggest_consolidation(
    utxo_count: int,
    fee_rate: int,
    avg_utxo_value: int,
    address_type: str = _DEFAULT_ADDR_TYPE,
) -> dict:
    """Advise whether consolidating UTXOs is economical at the current fee rate.

    Parameters
    ----------
    utxo_count:
        Number of UTXOs in the wallet.
    fee_rate:
        Current fee rate in sat/vB.
    avg_utxo_value:
        Average UTXO value in satoshis.
    address_type:
        Type of the UTXOs.

    Returns
    -------
    dict with keys:
        should_consolidate (bool), consolidation_fee_sats,
        breakeven_fee_rate (int), future_savings_sats,
        individual_spend_fee_sats, recommendation (str)
    """
    input_vb = _INPUT_VBYTES.get(address_type, _INPUT_VBYTES[_DEFAULT_ADDR_TYPE])

    # Fee to consolidate all UTXOs into 1 output now
    consolidation_size = estimate_tx_size(utxo_count, 1, address_type)
    consolidation_fee = consolidation_size["vbytes"] * fee_rate

    # Fee to spend each UTXO individually in the future (at same rate)
    individual_fee_each = estimate_tx_size(1, 2, address_type)["vbytes"] * fee_rate
    total_individual_fees = individual_fee_each * utxo_count

    future_savings = total_individual_fees - consolidation_fee - (individual_fee_each * utxo_count)

    # Breakeven: at what fee rate does consolidation become worthwhile?
    # When consolidation_fee < savings from reduced future input sizes
    # Each consolidated input saves (input_vb * future_rate) sats in future txs
    # Simplified: consolidate if fee per input < 3x input vbytes (heuristic)
    per_input_consolidation_fee = consolidation_fee / utxo_count if utxo_count > 0 else 0
    breakeven_rate = int(per_input_consolidation_fee / (input_vb * 2)) if input_vb > 0 else 0

    # Rule of thumb: consolidate if utxo_count > 5 and fee is low (< 20 sat/vB)
    should_consolidate = utxo_count > 5 and fee_rate <= 20 and avg_utxo_value > consolidation_fee

    if not should_consolidate:
        if fee_rate > 50:
            rec = f"Fee rate is high ({fee_rate} sat/vB). Wait for lower fees to consolidate."
        elif utxo_count <= 5:
            rec = f"Only {utxo_count} UTXOs — consolidation not necessary yet."
        elif avg_utxo_value <= consolidation_fee:
            rec = "Average UTXO value is smaller than the consolidation fee. Do not consolidate."
        else:
            rec = "Consolidation not recommended at current conditions."
    else:
        rec = (
            f"Consider consolidating {utxo_count} UTXOs now at {fee_rate} sat/vB. "
            f"Consolidation cost: {consolidation_fee} sats."
        )

    return {
        "should_consolidate": should_consolidate,
        "utxo_count": utxo_count,
        "consolidation_fee_sats": consolidation_fee,
        "individual_spend_fee_sats": individual_fee_each,
        "breakeven_fee_rate": breakeven_rate,
        "future_savings_sats": max(0, total_individual_fees - consolidation_fee),
        "recommendation": rec,
    }


# ---------------------------------------------------------------------------
# Fee tiers
# ---------------------------------------------------------------------------

def get_fee_tiers() -> list:
    """Return standard fee tier definitions with estimated confirmation times.

    Returns
    -------
    list of dict, each with keys:
        tier, label, sat_per_vbyte_min, sat_per_vbyte_max,
        est_blocks, est_minutes, description
    """
    return [
        {
            "tier": "no_priority",
            "label": "No Priority",
            "sat_per_vbyte_min": 1,
            "sat_per_vbyte_max": 2,
            "est_blocks": "144+",
            "est_minutes": "1440+",
            "description": "May take a day or more. Suitable for non-urgent batch consolidations.",
        },
        {
            "tier": "low",
            "label": "Low Priority",
            "sat_per_vbyte_min": 2,
            "sat_per_vbyte_max": 5,
            "est_blocks": "12-144",
            "est_minutes": "120-1440",
            "description": "Typically confirmed within a few hours. Good for savings movements.",
        },
        {
            "tier": "medium",
            "label": "Medium Priority",
            "sat_per_vbyte_min": 5,
            "sat_per_vbyte_max": 20,
            "est_blocks": "3-12",
            "est_minutes": "30-120",
            "description": "Confirmed within 30 minutes to 2 hours under normal conditions.",
        },
        {
            "tier": "high",
            "label": "High Priority",
            "sat_per_vbyte_min": 20,
            "sat_per_vbyte_max": 50,
            "est_blocks": "1-3",
            "est_minutes": "10-30",
            "description": "Likely confirmed in the next 1-3 blocks.",
        },
        {
            "tier": "urgent",
            "label": "Urgent",
            "sat_per_vbyte_min": 50,
            "sat_per_vbyte_max": 500,
            "est_blocks": "1",
            "est_minutes": "~10",
            "description": "Next-block confirmation. Use during mempool congestion or time-sensitive payments.",
        },
    ]


# ---------------------------------------------------------------------------
# Batching savings
# ---------------------------------------------------------------------------


def calculate_batching_savings(
    tx_count: int,
    fee_rate: int,
    address_type: str = _DEFAULT_ADDR_TYPE,
) -> dict:
    """Calculate fee savings from batching multiple transactions into one.

    Batching N payments into a single transaction with N outputs instead
    of N separate 1-output transactions saves on the overhead and input
    costs paid multiple times.

    Parameters
    ----------
    tx_count:
        Number of payments to batch.
    fee_rate:
        Fee rate in sat/vB.
    address_type:
        Input address type (assumes 1 input per transaction).

    Returns
    -------
    dict with keys:
        unbatched_fee_sats, batched_fee_sats, savings_sats,
        savings_pct, tx_count, fee_rate_svb
    """
    if tx_count < 2:
        return {
            "unbatched_fee_sats": 0,
            "batched_fee_sats": 0,
            "savings_sats": 0,
            "savings_pct": 0.0,
            "tx_count": tx_count,
            "fee_rate_svb": fee_rate,
            "note": "Batching requires at least 2 transactions.",
        }

    # Unbatched: each tx has 1 input, 2 outputs (recipient + change)
    single_vb = estimate_tx_size(1, 2, address_type)["vbytes"]
    unbatched_fee = single_vb * fee_rate * tx_count

    # Batched: 1 input, N+1 outputs (all recipients + 1 change)
    batched_vb = estimate_tx_size(1, tx_count + 1, address_type)["vbytes"]
    batched_fee = batched_vb * fee_rate

    savings = unbatched_fee - batched_fee
    savings_pct = (savings / unbatched_fee * 100) if unbatched_fee > 0 else 0.0

    return {
        "unbatched_fee_sats": unbatched_fee,
        "batched_fee_sats": batched_fee,
        "savings_sats": savings,
        "savings_pct": round(savings_pct, 1),
        "tx_count": tx_count,
        "fee_rate_svb": fee_rate,
        "unbatched_vbytes_total": single_vb * tx_count,
        "batched_vbytes": batched_vb,
    }
