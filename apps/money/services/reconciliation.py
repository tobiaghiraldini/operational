"""Match BankStatementLine rows to existing Transaction rows."""
from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal
from typing import Iterable

from django.db import transaction as db_transaction

from apps.money.models import BankStatement, BankStatementLine, Transaction

logger = logging.getLogger(__name__)

DEFAULT_DATE_TOLERANCE_DAYS = 3


@db_transaction.atomic
def auto_match_lines(
    statement: BankStatement,
    *,
    tolerance_days: int = DEFAULT_DATE_TOLERANCE_DAYS,
) -> dict:
    """For every line in `statement` try to find a matching Transaction.

    Match heuristic:
    - same `account` as the statement
    - `direction` matches
    - `amount` exactly equal
    - `date` within ±tolerance_days
    - transaction not already matched to another line

    Returns a stats dict: `{matched: N, unmatched: N, total: N}`.
    """
    lines = list(statement.lines.filter(is_matched=False))
    matched = 0
    used_tx_ids: set[int] = set()

    for line in lines:
        candidate = _find_candidate(
            account_id=statement.account_id,
            direction=line.direction,
            amount=line.amount,
            on_date=line.date,
            tolerance_days=tolerance_days,
            exclude_ids=used_tx_ids,
        )
        if candidate:
            line.matched_transaction = candidate
            line.is_matched = True
            line.save(update_fields=["matched_transaction", "is_matched", "updated_at"])
            used_tx_ids.add(candidate.id)
            matched += 1

    return {
        "matched": matched,
        "unmatched": len(lines) - matched,
        "total": len(lines),
    }


def _find_candidate(
    *,
    account_id: int,
    direction: str,
    amount: Decimal,
    on_date,
    tolerance_days: int,
    exclude_ids: Iterable[int],
) -> Transaction | None:
    earliest = on_date - timedelta(days=tolerance_days)
    latest = on_date + timedelta(days=tolerance_days)
    qs = (
        Transaction.objects.filter(
            account_id=account_id,
            direction=direction,
            amount=amount,
            date__gte=earliest,
            date__lte=latest,
            bank_statement_line__isnull=True,
        )
        .exclude(id__in=list(exclude_ids))
        .order_by("date")
    )
    return qs.first()


@db_transaction.atomic
def materialize_unmatched(
    statement: BankStatement,
    *,
    default_category_id: int | None = None,
) -> int:
    """Create one `Transaction` per unmatched `BankStatementLine`.

    Useful when the user trusts the bank as the source of truth and wants the
    daybook auto-populated from the statement.
    """
    unmatched = list(
        statement.lines.filter(is_matched=False, matched_transaction__isnull=True)
    )
    created = 0
    for line in unmatched:
        tx = Transaction.objects.create(
            date=line.date,
            direction=line.direction,
            amount=line.amount,
            currency=statement.account.currency,
            account=statement.account,
            category_id=default_category_id,
            counterparty="",
            description=line.description,
            reference=line.bank_reference,
            bank_statement_line=line,
        )
        line.matched_transaction = tx
        line.is_matched = True
        line.save(update_fields=["matched_transaction", "is_matched", "updated_at"])
        created += 1
    return created
