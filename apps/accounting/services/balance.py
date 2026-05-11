"""Per-account balance reconciliation services."""
from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from django.db import transaction as db_transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounting.models import FiscalPeriod, PeriodAccountBalance
from apps.accounting.services.period import period_date_range, previous_period
from apps.money.models import Account, Transaction


@db_transaction.atomic
def recompute_period_balances(
    period: FiscalPeriod,
    *,
    only_account_ids: Iterable[int] | None = None,
) -> list[PeriodAccountBalance]:
    """Refresh `PeriodAccountBalance` rows for every active Account in `period`.

    For each account:
    - `starting_balance`: previous period's `ending_balance` (or the account's
      `opening_balance` when there's no previous period and no value yet set).
    - `computed_flow`: signed sum of in/out Transactions in the period range.
    - `computed_ending`: starting + flow.
    - `discrepancy`: ending_balance - computed_ending (zero means balanced).

    Idempotent: safe to call repeatedly. Returns the refreshed rows.
    """
    accounts_qs = Account.objects.filter(is_active=True)
    if only_account_ids is not None:
        accounts_qs = accounts_qs.filter(id__in=list(only_account_ids))

    date_from, date_to = period_date_range(period)
    prev = previous_period(period)

    refreshed: list[PeriodAccountBalance] = []
    for account in accounts_qs:
        bal, created = PeriodAccountBalance.objects.get_or_create(
            period=period, account=account
        )

        if not bal.opening_confirmed_at and (
            created or bal.starting_balance == Decimal("0")
        ):
            bal.starting_balance = _initial_starting_balance(account, prev)

        bal.computed_flow = _signed_flow(account, date_from, date_to)
        bal.computed_ending = bal.starting_balance + bal.computed_flow
        bal.discrepancy = bal.ending_balance - bal.computed_ending
        bal.is_balanced = bal.discrepancy == Decimal("0") and bal.ending_balance != Decimal("0")
        bal.last_reconciled_at = timezone.now()
        bal.save()
        refreshed.append(bal)
    return refreshed


def _initial_starting_balance(account: Account, prev: FiscalPeriod | None) -> Decimal:
    if prev is not None:
        prev_bal = PeriodAccountBalance.objects.filter(
            period=prev, account=account
        ).first()
        if prev_bal:
            return prev_bal.ending_balance or prev_bal.computed_ending
    return account.opening_balance or Decimal("0")


def _signed_flow(account: Account, date_from, date_to) -> Decimal:
    inflow = (
        Transaction.objects.filter(
            account=account,
            direction=Transaction.DIRECTION_IN,
            date__gte=date_from,
            date__lte=date_to,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )
    outflow = (
        Transaction.objects.filter(
            account=account,
            direction=Transaction.DIRECTION_OUT,
            date__gte=date_from,
            date__lte=date_to,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )
    return inflow - outflow


def set_reported_ending_balance(
    period: FiscalPeriod,
    account: Account,
    ending_balance: Decimal,
) -> PeriodAccountBalance:
    """Set the reported ending balance for an account and refresh derived fields."""
    bal, _ = PeriodAccountBalance.objects.get_or_create(
        period=period, account=account
    )
    bal.ending_balance = Decimal(ending_balance)
    bal.save(update_fields=["ending_balance", "updated_at"])
    return recompute_period_balances(period, only_account_ids=[account.id])[0]


@db_transaction.atomic
def confirm_opening_balance(
    period: FiscalPeriod,
    account: Account,
    user,
    *,
    starting_balance: Decimal | None = None,
) -> PeriodAccountBalance:
    """Audit-stamp the opening balance for `account` on `period` and recompute.

    If `starting_balance` is provided, it overrides the row's current value
    before stamping (this lets the admin form save and confirm in one step).
    The user is recorded as `opening_confirmed_by`.
    """
    bal, _ = PeriodAccountBalance.objects.get_or_create(
        period=period, account=account
    )
    if starting_balance is not None:
        bal.starting_balance = Decimal(starting_balance)
    bal.opening_confirmed_at = timezone.now()
    bal.opening_confirmed_by = user if getattr(user, "is_authenticated", False) else None
    bal.save(
        update_fields=[
            "starting_balance",
            "opening_confirmed_at",
            "opening_confirmed_by",
            "updated_at",
        ]
    )
    return recompute_period_balances(period, only_account_ids=[account.id])[0]
