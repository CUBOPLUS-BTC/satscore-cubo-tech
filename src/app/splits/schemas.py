"""Validation helpers for split profiles and rules."""

from __future__ import annotations


def validate_label(label) -> str:
    if not label or not isinstance(label, str):
        raise ValueError("label requerido")
    label = label.strip()
    if len(label) > 80:
        raise ValueError("label máximo 80 caracteres")
    return label


def validate_percentage(pct) -> int:
    try:
        pct = int(pct)
    except (TypeError, ValueError):
        raise ValueError("percentage debe ser entero")
    if pct < 1 or pct > 100:
        raise ValueError("percentage debe estar entre 1 y 100")
    return pct


def validate_rules_total(rules: list[dict]) -> None:
    """Ensure percentages add up to exactly 100."""
    total = sum(r["percentage"] for r in rules)
    if total != 100:
        raise ValueError(
            f"Los porcentajes suman {total}%, deben sumar exactamente 100%"
        )
