"""Helpers around `FiscalPeriod` lookup and date arithmetic."""
from __future__ import annotations

import calendar
from datetime import date as date_cls
from typing import Iterable, Tuple

from django.utils import timezone

from apps.accounting.models import FiscalPeriod


def current_period(today: date_cls | None = None) -> FiscalPeriod:
    """Return the FiscalPeriod for `today` (defaults to local date), creating it if needed."""
    today = today or timezone.localdate()
    period, _ = FiscalPeriod.objects.get_or_create(year=today.year, month=today.month)
    return period


def get_or_create_period(year: int, month: int) -> FiscalPeriod:
    period, _ = FiscalPeriod.objects.get_or_create(year=year, month=month)
    return period


def period_date_range(period: FiscalPeriod) -> Tuple[date_cls, date_cls]:
    last_day = calendar.monthrange(period.year, period.month)[1]
    return (
        date_cls(period.year, period.month, 1),
        date_cls(period.year, period.month, last_day),
    )


def calendar_year_bounds(year: int) -> Tuple[date_cls, date_cls]:
    """Inclusive Jan 1 … Dec 31 for a calendar year."""
    return date_cls(year, 1, 1), date_cls(year, 12, 31)


def previous_period(period: FiscalPeriod) -> FiscalPeriod | None:
    """Return the period immediately before `period`, or None if it doesn't exist."""
    if period.month == 1:
        prev_year, prev_month = period.year - 1, 12
    else:
        prev_year, prev_month = period.year, period.month - 1
    return FiscalPeriod.objects.filter(year=prev_year, month=prev_month).first()


def list_periods(limit: int = 24) -> Iterable[FiscalPeriod]:
    return FiscalPeriod.objects.order_by("-year", "-month")[:limit]
