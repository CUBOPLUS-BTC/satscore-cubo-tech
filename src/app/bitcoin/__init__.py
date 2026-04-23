"""Bitcoin utilities module for the Magma app.

Provides address validation, unit conversion, fee estimation,
and transaction analysis utilities — all pure-Python, no external
dependencies.
"""

from .address import validate_address, get_address_type, is_mainnet, is_testnet
from .units import sats_to_btc, btc_to_sats, sats_to_usd, usd_to_sats, format_sats, format_btc
from .fees import estimate_tx_fee, get_fee_tiers
from .transactions import estimate_confirmation_time, classify_transaction

__all__ = [
    "validate_address",
    "get_address_type",
    "is_mainnet",
    "is_testnet",
    "sats_to_btc",
    "btc_to_sats",
    "sats_to_usd",
    "usd_to_sats",
    "format_sats",
    "format_btc",
    "estimate_tx_fee",
    "get_fee_tiers",
    "estimate_confirmation_time",
    "classify_transaction",
]
