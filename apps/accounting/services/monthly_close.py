"""Close (or lock) a fiscal period after the user reconciles balances."""
from __future__ import annotations

from typing import Mapping

from django.db import transaction as db_transaction
from django.utils import timezone

from apps.accounting.models import FiscalPeriod
from apps.accounting.services.balance import (
    recompute_period_balances,
    set_reported_ending_balance,
)
from apps.money.models import Account


class PeriodNotBalancedError(RuntimeError):
    """Raised when a period close is attempted while at least one account is off."""


@db_transaction.atomic
def close_period(
    period: FiscalPeriod,
    *,
    ending_balances: Mapping[int, str | float] | None = None,
    user=None,
    force: bool = False,
) -> FiscalPeriod:
    """Mark `period` as closed.

    `ending_balances`: optional `{account_id: ending_balance}` map applied
    before the close so the user can do "reconcile + close" in one shot.
    `force`: when False, the close fails if any `PeriodAccountBalance` is not
    balanced; when True the close proceeds and the discrepancies are kept on
    record.
    """
    if ending_balances:
        for account_id, ending in ending_balances.items():
            account = Account.objects.filter(id=account_id, is_active=True).first()
            if not account:
                continue
            set_reported_ending_balance(period, account, ending)

    balances = recompute_period_balances(period)
    if not force:
        unbalanced = [b for b in balances if not b.is_balanced]
        if unbalanced:
            names = ", ".join(b.account.name for b in unbalanced)
            raise PeriodNotBalancedError(
                f"Cannot close {period.label}: unbalanced accounts -> {names}"
            )

    period.status = FiscalPeriod.STATUS_CLOSED
    period.closed_at = timezone.now()
    period.closed_by = user
    period.save(update_fields=["status", "closed_at", "closed_by", "updated_at"])
    return period


@db_transaction.atomic
def reopen_period(period: FiscalPeriod) -> FiscalPeriod:
    """Move `period` back to OPEN. Locked periods are left untouched."""
    if period.status == FiscalPeriod.STATUS_LOCKED:
        return period
    period.status = FiscalPeriod.STATUS_OPEN
    period.closed_at = None
    period.closed_by = None
    period.save(update_fields=["status", "closed_at", "closed_by", "updated_at"])
    return period
