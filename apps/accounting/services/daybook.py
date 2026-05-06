"""Daybook (Prima Nota) builder."""
from __future__ import annotations

from datetime import date as date_cls
from decimal import Decimal
from typing import Iterable

from django.db.models import QuerySet

from apps.money.models import Transaction


def build_daybook(
    *,
    date_from: date_cls,
    date_to: date_cls,
    account_id: int | None = None,
    direction: str | None = None,
    category_id: int | None = None,
) -> QuerySet[Transaction]:
    """Return a chronological QuerySet of Transactions.

    The result is the canonical "prima nota" feed: each Transaction is one
    line. Eager-loads related entities the daybook UI/exports always show.
    """
    qs = (
        Transaction.objects.select_related(
            "account",
            "account__currency",
            "category",
            "currency",
            "invoice",
            "customer",
            "vendor",
        )
        .filter(date__gte=date_from, date__lte=date_to)
        .order_by("date", "id")
    )
    if account_id:
        qs = qs.filter(account_id=account_id)
    if direction:
        qs = qs.filter(direction=direction)
    if category_id:
        qs = qs.filter(category_id=category_id)
    return qs


def daybook_with_running_balance(
    transactions: Iterable[Transaction],
    *,
    starting_balance: Decimal = Decimal("0"),
) -> list[dict]:
    """Add a running balance to each daybook row.

    Single-account aware: the caller should normally pre-filter by `account_id`
    so the running balance makes sense. When mixing accounts the running
    balance simply represents a global signed cash flow.
    """
    rows: list[dict] = []
    balance = Decimal(starting_balance)
    for tx in transactions:
        balance += tx.signed_amount
        rows.append({"transaction": tx, "balance": balance})
    return rows
