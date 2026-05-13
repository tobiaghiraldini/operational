"""Convert invoice currency amounts into a transaction's settlement currency using stored rates."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from apps.money.models import ExchangeRate


def amount_in_transaction_currency(
    *,
    amount: Decimal,
    from_currency_id: int,
    to_currency_id: int,
    as_of: date,
) -> Decimal | None:
    """Return `amount` in `to_currency` using the latest rate on or before `as_of`.

    Looks up direct `from → to` then inverse `to → from`. Returns ``None`` if
    no usable rate exists (caller should ask for a manual amount or add rates).
    """
    if from_currency_id == to_currency_id:
        return amount

    direct = (
        ExchangeRate.objects.filter(
            from_currency_id=from_currency_id,
            to_currency_id=to_currency_id,
            valid_from__lte=as_of,
        )
        .order_by("-valid_from")
        .values_list("rate", flat=True)
        .first()
    )
    if direct is not None:
        return (amount * direct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    inverse = (
        ExchangeRate.objects.filter(
            from_currency_id=to_currency_id,
            to_currency_id=from_currency_id,
            valid_from__lte=as_of,
        )
        .order_by("-valid_from")
        .values_list("rate", flat=True)
        .first()
    )
    if inverse is not None and inverse != 0:
        return (amount / inverse).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return None
