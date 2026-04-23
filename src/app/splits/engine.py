"""Non-custodial split engine.

Given a split profile and an amount, produces one LNURL-pay invoice per rule.
Magma never receives or holds any sats — invoices point directly to each
recipient's Lightning wallet.
"""

from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from .manager import SplitsManager
from ..sends.executor import SendExecutor


# Resolve invoices in parallel (one HTTP call per recipient wallet)
_POOL = ThreadPoolExecutor(max_workers=5)


class SplitEngine:
    """Build multiple invoices for a split profile."""

    def __init__(
        self,
        splits_manager: SplitsManager,
        send_executor: SendExecutor,
    ) -> None:
        self.splits = splits_manager
        self.executor = send_executor

    def build_split(
        self,
        profile_id: int,
        pubkey: str,
        amount_usd: float,
        comment: Optional[str] = None,
    ) -> dict:
        """Return a list of invoices — one per split rule.

        The sender pays each invoice independently from their own wallet.
        Magma never custodies funds.

        Returns::

            {
                "profile": { ... },
                "total_usd": 12.50,
                "total_sats": 12345,
                "btc_price_usd": 101234.56,
                "invoices": [
                    {
                        "rule": { recipient_name, percentage, label },
                        "amount_usd": 7.50,
                        "amount_sats": 7407,
                        "bolt11": "lnbc...",
                        "deeplink": "lightning:lnbc...",
                        "status": "ready"        # or "error"
                    },
                    ...
                ],
                "all_ready": true,
                "custody_model": "none"
            }
        """
        if amount_usd is None or amount_usd <= 0:
            raise ValueError("amount_usd debe ser mayor a 0")
        if amount_usd > 100_000:
            raise ValueError("amount_usd excede el máximo permitido")

        profile = self.splits.get_profile(profile_id, pubkey)
        rules = profile.get("rules", [])
        if not rules:
            raise ValueError("El perfil no tiene reglas configuradas")

        # Get current BTC price once (shared across all splits)
        btc_price = self.executor._current_btc_price()
        if btc_price <= 0:
            raise ValueError("Precio BTC no disponible en este momento")

        total_sats = int(round((amount_usd / btc_price) * 100_000_000))

        # Calculate sats per rule, handling rounding so total is exact
        allocations = self._allocate_sats(rules, total_sats)

        # Resolve invoices in parallel — each call is an independent HTTPS
        # request to the recipient's LNURL-pay server
        invoices = []
        futures = {}
        for rule, rule_sats in allocations:
            rule_usd = round((rule_sats / 100_000_000) * btc_price, 2)
            fut = _POOL.submit(
                self._resolve_single_invoice,
                rule,
                rule_sats,
                rule_usd,
                comment,
            )
            futures[fut] = (rule, rule_sats, rule_usd)

        for fut in as_completed(futures):
            rule, rule_sats, rule_usd = futures[fut]
            invoices.append(fut.result())

        # Sort by priority to match the user's intended order
        invoices.sort(key=lambda i: i["rule"].get("priority", 0))

        all_ready = all(i["status"] == "ready" for i in invoices)

        return {
            "profile": {
                "id": profile["id"],
                "label": profile["label"],
            },
            "total_usd": round(amount_usd, 2),
            "total_sats": total_sats,
            "btc_price_usd": round(btc_price, 2),
            "invoices": invoices,
            "all_ready": all_ready,
            "custody_model": "none",
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _allocate_sats(
        rules: list[dict], total_sats: int
    ) -> list[tuple[dict, int]]:
        """Distribute sats by percentage, rounding carefully.

        The largest-remainder method ensures the sum is always exact.
        """
        raw = []
        for r in rules:
            exact = (r["percentage"] / 100) * total_sats
            floored = math.floor(exact)
            raw.append((r, floored, exact - floored))

        allocated = sum(f for _, f, _ in raw)
        remainder = total_sats - allocated

        # Give extra sats to rules with biggest fractional remainder
        raw.sort(key=lambda x: x[2], reverse=True)
        result = []
        for i, (rule, floored, _frac) in enumerate(raw):
            if i < remainder:
                result.append((rule, floored + 1))
            else:
                result.append((rule, floored))

        return result

    def _resolve_single_invoice(
        self,
        rule: dict,
        amount_sats: int,
        amount_usd: float,
        comment: Optional[str],
    ) -> dict:
        """Build one invoice for a single split rule.

        On failure, returns a partial result with status="error" so the
        sender can still pay the rules that succeeded.
        """
        base = {
            "rule": {
                "id": rule.get("id"),
                "recipient_name": rule.get("recipient_name", ""),
                "recipient_ln": rule.get("recipient_ln", ""),
                "percentage": rule["percentage"],
                "priority": rule.get("priority", 0),
                "label": rule.get("label", ""),
            },
            "amount_usd": amount_usd,
            "amount_sats": amount_sats,
        }

        if amount_sats <= 0:
            return {**base, "bolt11": None, "deeplink": None, "status": "skip",
                    "error": "Monto muy pequeño para esta regla"}

        ln_address = rule.get("recipient_ln", "")
        if not ln_address:
            return {**base, "bolt11": None, "deeplink": None, "status": "error",
                    "error": "Recipient sin lightning address"}

        try:
            amount_msat = amount_sats * 1000
            meta = self.executor.recipients.resolve_lnurl_pay(ln_address)
            callback = meta["callback"]

            # Validate against wallet limits
            min_msat = meta.get("min_sendable_msat", 0)
            max_msat = meta.get("max_sendable_msat", 0)
            if min_msat and amount_msat < int(min_msat):
                return {
                    **base, "bolt11": None, "deeplink": None, "status": "error",
                    "error": f"Bajo el mínimo de la wallet ({int(min_msat) // 1000} sats)",
                }
            if max_msat and amount_msat > int(max_msat):
                return {
                    **base, "bolt11": None, "deeplink": None, "status": "error",
                    "error": f"Sobre el máximo de la wallet ({int(max_msat) // 1000} sats)",
                }

            invoice_data = self.executor._call_callback(
                callback, amount_msat, comment
            )
            bolt11 = invoice_data.get("pr", "")

            return {
                **base,
                "bolt11": bolt11,
                "deeplink": f"lightning:{bolt11}" if bolt11 else None,
                "status": "ready",
            }
        except Exception as exc:
            return {
                **base,
                "bolt11": None,
                "deeplink": None,
                "status": "error",
                "error": str(exc),
            }
