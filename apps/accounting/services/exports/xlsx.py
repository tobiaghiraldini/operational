"""Generate the monthly XLS package the accountant receives.

Sheets, in order:

1. Daybook       chronological cash/bank flows
2. Income & Expenses    totals by category
3. Balance       per-account opening/flow/closing/discrepancy
4. Issued Invoices
5. Received Invoices
6. Bank Statement Lines (matched / unmatched)

Uses `openpyxl` directly so we can apply header styling, frozen panes, and
currency formats without bringing in a heavier dependency.
"""
from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from typing import Any

from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from apps.accounting.models import (
    AccountingExport,
    FiscalPeriod,
    PeriodAccountBalance,
)
from apps.accounting.services.balance import recompute_period_balances
from apps.accounting.services.daybook import build_daybook
from apps.accounting.services.income_statement import build_income_statement
from apps.accounting.services.period import period_date_range
from apps.invoices.models import Invoice
from apps.money.models import BankStatementLine, Transaction


HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="1F2937")
ZEBRA_FILL = PatternFill("solid", fgColor="F9FAFB")
RED_FILL = PatternFill("solid", fgColor="FEE2E2")
GREEN_FILL = PatternFill("solid", fgColor="DCFCE7")

CURRENCY_FORMAT = '#,##0.00;[Red]-#,##0.00'


def build_monthly_workbook(period: FiscalPeriod) -> BytesIO:
    """Return an in-memory XLSX `BytesIO` for `period`."""
    workbook = Workbook()
    workbook.remove(workbook.active)

    _add_daybook_sheet(workbook, period)
    _add_income_statement_sheet(workbook, period)
    _add_balance_sheet(workbook, period)
    _add_invoices_sheet(workbook, period, kind="emitted", title="Issued Invoices")
    _add_invoices_sheet(workbook, period, kind="received", title="Received Invoices")
    _add_bank_lines_sheet(workbook, period)

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


def build_workbook_response(
    period: FiscalPeriod, *, user=None
) -> HttpResponse:
    """Build the workbook, persist an `AccountingExport` audit row, return HttpResponse."""
    buffer = build_monthly_workbook(period)
    file_name = f"accounting_{period.label}.xlsx"

    AccountingExport.objects.create(
        period=period,
        kind=AccountingExport.KIND_FULL_PACKAGE,
        file_name=file_name,
        generated_by=user,
        parameters_json={"period": period.label},
    )

    response = HttpResponse(
        buffer.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = f'attachment; filename="{file_name}"'
    return response


# ---------------------------------------------------------------------------
# Sheet builders
# ---------------------------------------------------------------------------


def _add_daybook_sheet(workbook: Workbook, period: FiscalPeriod) -> None:
    sheet = workbook.create_sheet("Daybook")
    headers = [
        "Date",
        "Doc #",
        "Counterparty",
        "Description",
        "Account",
        "Category",
        "In",
        "Out",
        "Currency",
        "Balance",
    ]
    _write_header(sheet, headers)

    date_from, date_to = period_date_range(period)
    transactions = build_daybook(date_from=date_from, date_to=date_to)

    balance = Decimal("0")
    for row_idx, tx in enumerate(transactions, start=2):
        balance += tx.signed_amount
        in_amount = tx.amount if tx.direction == Transaction.DIRECTION_IN else None
        out_amount = tx.amount if tx.direction == Transaction.DIRECTION_OUT else None

        row = [
            tx.date,
            tx.reference or (tx.invoice.invoice_number if tx.invoice else ""),
            tx.counterparty
            or (tx.customer.name if tx.customer else "")
            or (tx.vendor.name if tx.vendor else ""),
            tx.description,
            tx.account.name if tx.account else "",
            tx.category.name if tx.category else "",
            in_amount,
            out_amount,
            tx.currency.code if tx.currency else "",
            balance,
        ]
        _write_row(sheet, row_idx, row, zebra=row_idx % 2 == 0)
        for col in (7, 8, 10):
            sheet.cell(row=row_idx, column=col).number_format = CURRENCY_FORMAT

    _autosize(sheet, headers)
    sheet.freeze_panes = "A2"


def _add_income_statement_sheet(workbook: Workbook, period: FiscalPeriod) -> None:
    sheet = workbook.create_sheet("Income & Expenses")
    headers = ["Category", "Income", "Expense", "Net"]
    _write_header(sheet, headers)

    summary = build_income_statement(period)
    income_lookup = {row["category_id"]: row for row in summary["income_by_category"]}
    expense_lookup = {row["category_id"]: row for row in summary["expense_by_category"]}
    keys = list({*income_lookup.keys(), *expense_lookup.keys()})

    row_idx = 2
    for cat_id in keys:
        income_row = income_lookup.get(cat_id, {"name": "Uncategorized", "total": Decimal("0")})
        expense_row = expense_lookup.get(cat_id, {"name": income_row.get("name", "Uncategorized"), "total": Decimal("0")})
        name = income_row.get("name") or expense_row.get("name") or "Uncategorized"
        income = income_row.get("total", Decimal("0"))
        expense = expense_row.get("total", Decimal("0"))
        _write_row(
            sheet,
            row_idx,
            [name, income, expense, income - expense],
            zebra=row_idx % 2 == 0,
        )
        for col in (2, 3, 4):
            sheet.cell(row=row_idx, column=col).number_format = CURRENCY_FORMAT
        row_idx += 1

    total_row = [
        "TOTAL",
        summary["total_income"],
        summary["total_expense"],
        summary["net"],
    ]
    _write_row(sheet, row_idx, total_row, bold=True)
    for col in (2, 3, 4):
        sheet.cell(row=row_idx, column=col).number_format = CURRENCY_FORMAT

    _autosize(sheet, headers)
    sheet.freeze_panes = "A2"


def _add_balance_sheet(workbook: Workbook, period: FiscalPeriod) -> None:
    sheet = workbook.create_sheet("Balance")
    headers = [
        "Account",
        "Currency",
        "Opening",
        "Total In",
        "Total Out",
        "Computed Closing",
        "Reported Closing",
        "Discrepancy",
        "OK?",
    ]
    _write_header(sheet, headers)

    recompute_period_balances(period)
    rows = (
        PeriodAccountBalance.objects.filter(period=period)
        .select_related("account", "account__currency")
        .order_by("account__name")
    )
    date_from, date_to = period_date_range(period)

    row_idx = 2
    for bal in rows:
        in_total = sum(
            (
                tx.amount
                for tx in Transaction.objects.filter(
                    account=bal.account,
                    direction=Transaction.DIRECTION_IN,
                    date__gte=date_from,
                    date__lte=date_to,
                )
            ),
            Decimal("0"),
        )
        out_total = sum(
            (
                tx.amount
                for tx in Transaction.objects.filter(
                    account=bal.account,
                    direction=Transaction.DIRECTION_OUT,
                    date__gte=date_from,
                    date__lte=date_to,
                )
            ),
            Decimal("0"),
        )
        ok_label = "Yes" if bal.is_balanced else "No"
        _write_row(
            sheet,
            row_idx,
            [
                bal.account.name,
                bal.account.currency.code if bal.account.currency_id else "",
                bal.starting_balance,
                in_total,
                out_total,
                bal.computed_ending,
                bal.ending_balance,
                bal.discrepancy,
                ok_label,
            ],
            zebra=row_idx % 2 == 0,
        )
        for col in (3, 4, 5, 6, 7, 8):
            sheet.cell(row=row_idx, column=col).number_format = CURRENCY_FORMAT
        ok_cell = sheet.cell(row=row_idx, column=9)
        ok_cell.fill = GREEN_FILL if bal.is_balanced else RED_FILL
        row_idx += 1

    _autosize(sheet, headers)
    sheet.freeze_panes = "A2"


def _add_invoices_sheet(workbook: Workbook, period: FiscalPeriod, *, kind: str, title: str) -> None:
    sheet = workbook.create_sheet(title)
    headers = [
        "Date",
        "#",
        "Counterparty",
        "Net",
        "VAT",
        "Gross",
        "Currency",
        "Status",
        "Paid On",
    ]
    _write_header(sheet, headers)

    date_from, date_to = period_date_range(period)
    invoices = (
        Invoice.objects.filter(
            invoice_type=kind,
            invoice_date__gte=date_from,
            invoice_date__lte=date_to,
        )
        .select_related("customer", "vendor")
        .order_by("invoice_date", "id")
    )
    for row_idx, invoice in enumerate(invoices, start=2):
        counterparty = ""
        if kind == "emitted" and invoice.customer:
            counterparty = invoice.customer.name
        elif kind == "received" and invoice.vendor:
            counterparty = invoice.vendor.name
        _write_row(
            sheet,
            row_idx,
            [
                invoice.invoice_date,
                invoice.invoice_number,
                counterparty,
                invoice.taxable_amount,
                invoice.vat_amount,
                invoice.total_amount,
                invoice.currency,
                invoice.status,
                invoice.payment_date,
            ],
            zebra=row_idx % 2 == 0,
        )
        for col in (4, 5, 6):
            sheet.cell(row=row_idx, column=col).number_format = CURRENCY_FORMAT

    _autosize(sheet, headers)
    sheet.freeze_panes = "A2"


def _add_bank_lines_sheet(workbook: Workbook, period: FiscalPeriod) -> None:
    sheet = workbook.create_sheet("Bank Lines")
    headers = ["Date", "Description", "Direction", "Amount", "Matched?", "Linked Tx"]
    _write_header(sheet, headers)

    date_from, date_to = period_date_range(period)
    lines = (
        BankStatementLine.objects.filter(
            date__gte=date_from, date__lte=date_to
        )
        .select_related("statement", "statement__account", "matched_transaction")
        .order_by("date", "id")
    )
    for row_idx, line in enumerate(lines, start=2):
        _write_row(
            sheet,
            row_idx,
            [
                line.date,
                line.description,
                line.direction,
                line.amount,
                "Yes" if line.is_matched else "No",
                str(line.matched_transaction) if line.matched_transaction else "",
            ],
            zebra=row_idx % 2 == 0,
        )
        sheet.cell(row=row_idx, column=4).number_format = CURRENCY_FORMAT
        match_cell = sheet.cell(row=row_idx, column=5)
        match_cell.fill = GREEN_FILL if line.is_matched else RED_FILL

    _autosize(sheet, headers)
    sheet.freeze_panes = "A2"


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _write_header(sheet: Worksheet, headers: list[str]) -> None:
    for col_idx, label in enumerate(headers, start=1):
        cell = sheet.cell(row=1, column=col_idx, value=label)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")


def _write_row(
    sheet: Worksheet,
    row_idx: int,
    values: list[Any],
    *,
    zebra: bool = False,
    bold: bool = False,
) -> None:
    for col_idx, value in enumerate(values, start=1):
        cell = sheet.cell(row=row_idx, column=col_idx, value=value)
        if zebra:
            cell.fill = ZEBRA_FILL
        if bold:
            cell.font = Font(bold=True)


def _autosize(sheet: Worksheet, headers: list[str]) -> None:
    for col_idx, label in enumerate(headers, start=1):
        max_len = len(str(label))
        column_letter = get_column_letter(col_idx)
        for cell in sheet[column_letter]:
            value = cell.value
            if value is None:
                continue
            length = len(str(value))
            if length > max_len:
                max_len = length
        sheet.column_dimensions[column_letter].width = min(max_len + 2, 40)
