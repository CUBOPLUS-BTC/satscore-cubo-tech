"""Non-custodial remittance split router.

Magma never touches sats.  It generates multiple LNURL-pay invoices — one per
split rule — so the sender pays each destination directly from their own wallet.
"""

from .manager import SplitsManager
from .engine import SplitEngine

__all__ = ["SplitsManager", "SplitEngine"]
