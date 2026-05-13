"""Income / expense aggregation by category for a fiscal period or date range."""
from __future__ import annotations

from collections import defaultdict
from datetime import date as date_cls
from decimal import Decimal

from django.db.models import Sum

from apps.accounting.models import FiscalPeriod
from apps.accounting.services.period import period_date_range
from apps.money.models import Transaction


def build_income_statement_for_range(
    date_from: date_cls, date_to: date_cls
) -> dict:
    """Aggregate income/expense totals by category between `date_from` and `date_to` (inclusive).

    Returns the same shape as `build_income_statement`, with ``period`` set to ``None``.
    """
    qs = (
        Transaction.objects.filter(date__gte=date_from, date__lte=date_to)
        .values("direction", "category__id", "category__name", "category__kind")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    income_rows: dict[int | None, dict] = defaultdict(
        lambda: {
            "category_id": None,
            "name": "Uncategorized",
            "kind": None,
            "total": Decimal("0"),
        }
    )
    expense_rows: dict[int | None, dict] = defaultdict(
        lambda: {
            "category_id": None,
            "name": "Uncategorized",
            "kind": None,
            "total": Decimal("0"),
        }
    )

    total_income = Decimal("0")
    total_expense = Decimal("0")

    for row in qs:
        bucket = (
            income_rows
            if row["direction"] == Transaction.DIRECTION_IN
            else expense_rows
        )
        cat_id = row["category__id"]
        entry = bucket[cat_id]
        entry["category_id"] = cat_id
        entry["name"] = row["category__name"] or "Uncategorized"
        entry["kind"] = row["category__kind"]
        entry["total"] += row["total"] or Decimal("0")
        if row["direction"] == Transaction.DIRECTION_IN:
            total_income += row["total"] or Decimal("0")
        else:
            total_expense += row["total"] or Decimal("0")

    return {
        "period": None,
        "date_from": date_from,
        "date_to": date_to,
        "income_by_category": sorted(
            income_rows.values(), key=lambda x: x["total"], reverse=True
        ),
        "expense_by_category": sorted(
            expense_rows.values(), key=lambda x: x["total"], reverse=True
        ),
        "total_income": total_income,
        "total_expense": total_expense,
        "net": total_income - total_expense,
    }


def build_income_statement(period: FiscalPeriod) -> dict:
    """Aggregate income/expense totals by category for `period`."""
    date_from, date_to = period_date_range(period)
    result = build_income_statement_for_range(date_from, date_to)
    result["period"] = period
    return result
