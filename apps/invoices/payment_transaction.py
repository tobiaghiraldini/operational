"""Create `money.Transaction` rows from invoice payment signals (extraction or manual flags)."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from apps.invoices.services import record_payment
from apps.money.models import Account

if TYPE_CHECKING:
    from apps.invoices.models import Invoice


def coerce_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def apply_extraction_payment_fields(invoice: "Invoice", extracted_data: dict) -> None:
    """Mutate `invoice` with payment_date / paid_override from LLM JSON (not saved)."""
    if not extracted_data:
        return
    pd = coerce_date(extracted_data.get("payment_date"))
    paid_flag = bool(extracted_data.get("paid_in_full") or extracted_data.get("is_paid"))
    if pd:
        invoice.payment_date = pd
        invoice.paid_override = False
    elif paid_flag:
        invoice.payment_date = None
        invoice.paid_override = True


def sync_invoice_payment_transaction(
    invoice: "Invoice",
    *,
    created_by=None,
) -> Optional[object]:
    """
    When the invoice is marked paid (payment_date or paid_override) and is not
    yet covered by linked transactions, post one payment to the default `Account`.

    Payment methods with `defer_bank_transaction` (e.g. credit card settled in a
    monthly bank batch) skip creating a `Transaction` until allocations are
    booked against the actual bank line.
    """
    if not invoice.total_amount or invoice.total_amount <= 0:
        return None
    if invoice.payments_total >= invoice.total_amount:
        return None
    if not invoice.payment_date and not getattr(invoice, "paid_override", False):
        return None

    pm = getattr(invoice, "payment_method", None)
    if pm is not None and getattr(pm, "defer_bank_transaction", False):
        return None

    account = (
        Account.objects.filter(is_default=True, is_active=True).order_by("id").first()
        or Account.objects.filter(is_active=True).order_by("id").first()
    )
    if account is None:
        return None

    pay_date = invoice.payment_date or invoice.invoice_date
    if pay_date is None:
        return None

    desc_extra = ""
    if invoice.payment_method_id:
        desc_extra = f" ({invoice.payment_method.name})"

    return record_payment(
        invoice,
        account=account,
        date=pay_date,
        description=f"Invoice {invoice.invoice_number}{desc_extra}",
        reference=invoice.invoice_number or "",
        created_by=created_by,
    )
