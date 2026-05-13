"""Resolve invoice currency ISO codes to tenant `money.Currency` rows."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.money.models import Currency


def resolve_invoice_currency(code: str | None) -> "Currency":
    """Return the currency for ``code``, falling back to EUR."""
    from apps.money.models import Currency

    raw = (code or "EUR").strip().upper()
    if len(raw) != 3:
        raw = "EUR"
    match = Currency.objects.filter(code=raw).first()
    if match:
        return match
    fallback = Currency.objects.filter(code="EUR").first()
    if fallback:
        return fallback
    raise ValueError(
        "No Currency row for EUR; configure tenant currencies before importing invoices."
    )
