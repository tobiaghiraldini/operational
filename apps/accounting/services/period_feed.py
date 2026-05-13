"""Unified per-period feed of transactions and unpaid invoices for the Daybook view."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from apps.accounting.models import FiscalPeriod, PeriodAccountBalance
from apps.accounting.services.daybook import build_daybook
from apps.accounting.services.period import period_date_range
from apps.invoices.models import Invoice
from apps.money.models import InvoiceSettlementAllocation, Transaction
from apps.money.services.invoice_document_label import transaction_invoice_document_label


ZERO = Decimal("0")


@dataclass
class PeriodFeed:
    """The full payload the Daybook admin change view consumes."""

    period: FiscalPeriod
    entries: list[dict[str, Any]] = field(default_factory=list)
    openings: list[PeriodAccountBalance] = field(default_factory=list)
    closings: list[PeriodAccountBalance] = field(default_factory=list)
    totals: dict[str, Decimal] = field(default_factory=dict)


def build_period_feed(period: FiscalPeriod) -> PeriodFeed:
    """Return the unified daybook feed for `period`.

    Composition:
      * `entries`: chronologically sorted list of dicts. Each entry has the
        following keys: `date`, `kind` ("transaction"/"invoice"), `doc_no`,
        `counterparty`, `account_label` (account name or "Unpaid" for
        invoices not yet paid in this period), `account_id` (or `None`),
        `description`, `direction` ("in"/"out"/None for invoices),
        `in` and `out` (Decimal amounts), `running` (per-account running
        balance after this entry, only for transactions), `source` (the
        underlying `Transaction` or `Invoice` instance).
      * `openings`/`closings`: per-account `PeriodAccountBalance` rows for
        the period, ordered by account name.
      * `totals`: aggregate `total_in`, `total_out`, `total_closing`,
        `total_starting`, `total_discrepancy` across accounts.

    Invoices already linked to a payment `Transaction` in this period are
    folded into the transaction line and do not appear as a separate
    "invoice" entry.
    """
    date_from, date_to = period_date_range(period)

    transactions = list(
        build_daybook(date_from=date_from, date_to=date_to)
    )

    tx_ids = [tx.id for tx in transactions]
    paid_invoice_ids = set(
        InvoiceSettlementAllocation.objects.filter(
            transaction_id__in=tx_ids,
            invoice_id__isnull=False,
        ).values_list("invoice_id", flat=True)
    )

    invoices = list(
        Invoice.objects.select_related("vendor", "customer", "currency")
        .filter(invoice_date__gte=date_from, invoice_date__lte=date_to)
        .exclude(id__in=paid_invoice_ids)
        .order_by("invoice_date", "id")
    )

    entries: list[dict[str, Any]] = []
    running_by_account: dict[int, Decimal] = {}

    balances = list(
        PeriodAccountBalance.objects.select_related("account", "account__currency")
        .filter(period=period)
        .order_by("account__name")
    )
    for bal in balances:
        running_by_account[bal.account_id] = Decimal(bal.starting_balance or ZERO)

    raw_entries: list[tuple[Any, str, Any]] = []
    for tx in transactions:
        raw_entries.append((tx.date, "transaction", tx))
    for inv in invoices:
        raw_entries.append((inv.invoice_date, "invoice", inv))

    raw_entries.sort(key=lambda row: (row[0], 0 if row[1] == "transaction" else 1))

    for entry_date, kind, source in raw_entries:
        if kind == "transaction":
            tx: Transaction = source
            in_amount = tx.amount if tx.direction == Transaction.DIRECTION_IN else ZERO
            out_amount = tx.amount if tx.direction == Transaction.DIRECTION_OUT else ZERO
            running_by_account[tx.account_id] = (
                running_by_account.get(tx.account_id, ZERO) + tx.signed_amount
            )
            entries.append(
                {
                    "date": entry_date,
                    "kind": "transaction",
                    "doc_no": transaction_invoice_document_label(tx),
                    "counterparty": _transaction_counterparty(tx),
                    "account_label": tx.account.name,
                    "account_id": tx.account_id,
                    "description": tx.description,
                    "direction": tx.direction,
                    "in": in_amount,
                    "out": out_amount,
                    "running": running_by_account[tx.account_id],
                    "source": tx,
                }
            )
        else:
            inv: Invoice = source
            in_amount, out_amount = _invoice_directional_amount(inv)
            entries.append(
                {
                    "date": entry_date,
                    "kind": "invoice",
                    "doc_no": inv.invoice_number,
                    "counterparty": _invoice_counterparty(inv),
                    "account_label": "Unpaid",
                    "account_id": None,
                    "description": inv.notes or "",
                    "direction": (
                        Transaction.DIRECTION_IN
                        if in_amount > ZERO
                        else Transaction.DIRECTION_OUT
                    ),
                    "in": in_amount,
                    "out": out_amount,
                    "running": None,
                    "source": inv,
                }
            )

    total_in = sum((e["in"] for e in entries), ZERO)
    total_out = sum((e["out"] for e in entries), ZERO)
    total_starting = sum((Decimal(b.starting_balance or ZERO) for b in balances), ZERO)
    total_closing = sum((Decimal(b.computed_ending or ZERO) for b in balances), ZERO)
    total_discrepancy = sum((Decimal(b.discrepancy or ZERO) for b in balances), ZERO)

    return PeriodFeed(
        period=period,
        entries=entries,
        openings=balances,
        closings=balances,
        totals={
            "total_in": total_in,
            "total_out": total_out,
            "total_starting": total_starting,
            "total_closing": total_closing,
            "total_discrepancy": total_discrepancy,
            "unpaid_invoice_count": Decimal(len(invoices)),
        },
    )


def _transaction_counterparty(tx: Transaction) -> str:
    if tx.counterparty:
        return tx.counterparty
    if tx.vendor_id and tx.vendor:
        return tx.vendor.name
    if tx.customer_id and tx.customer:
        return tx.customer.name
    return ""


def _invoice_counterparty(inv: Invoice) -> str:
    if inv.vendor_id and inv.vendor:
        return inv.vendor.name
    if inv.customer_id and inv.customer:
        return inv.customer.name
    return ""


def _invoice_directional_amount(inv: Invoice) -> tuple[Decimal, Decimal]:
    """Map invoice type to daybook in/out columns.

    - emitted invoice -> inbound amount
    - received invoice -> outbound amount
    """
    amount = Decimal(inv.total_amount or ZERO)
    if inv.invoice_type == "emitted":
        return amount, ZERO
    return ZERO, amount
