"""Currency conversion helpers."""
from __future__ import annotations

import logging
from datetime import date as date_cls
from decimal import Decimal
from typing import Optional

from django.utils import timezone

from apps.money.models import Currency, ExchangeRate

logger = logging.getLogger(__name__)


def get_rate(
    from_code: str,
    to_code: str,
    on_date: Optional[date_cls] = None,
) -> Optional[Decimal]:
    """Return the most recent rate <= on_date for a `from_code -> to_code` pair.

    Returns None when no rate is configured. Inverse and identity are short-circuited.
    """
    from_code = (from_code or "").upper().strip()
    to_code = (to_code or "").upper().strip()
    if not from_code or not to_code:
        return None
    if from_code == to_code:
        return Decimal("1")
    on_date = on_date or timezone.localdate()

    direct = (
        ExchangeRate.objects.filter(
            from_currency__code=from_code,
            to_currency__code=to_code,
            valid_from__lte=on_date,
        )
        .order_by("-valid_from")
        .first()
    )
    if direct:
        return direct.rate

    inverse = (
        ExchangeRate.objects.filter(
            from_currency__code=to_code,
            to_currency__code=from_code,
            valid_from__lte=on_date,
        )
        .order_by("-valid_from")
        .first()
    )
    if inverse and inverse.rate:
        return Decimal("1") / inverse.rate

    return None


def convert(
    amount: Decimal,
    from_code: str,
    to_code: str,
    on_date: Optional[date_cls] = None,
) -> tuple[Decimal, Optional[Decimal]]:
    """Convert `amount` from `from_code` to `to_code`.

    Returns `(converted_amount, rate_used)`. When no rate is found, falls back
    to 1.0 with a warning log so callers never crash on missing exchange data.
    """
    rate = get_rate(from_code, to_code, on_date)
    if rate is None:
        logger.warning(
            "No exchange rate %s->%s for %s; falling back to 1:1",
            from_code,
            to_code,
            on_date,
        )
        return amount, None
    return (amount * rate).quantize(Decimal("0.01")), rate


def ensure_currency(code: str) -> Optional[Currency]:
    """Return the active Currency for `code`, or None."""
    if not code:
        return None
    return Currency.objects.filter(code=code.upper().strip(), is_active=True).first()
