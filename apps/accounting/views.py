"""Views for the accounting feature.

Convention: every view that produces accounting data is wrapped with
`accounting_setup_required`, which redirects to the setup wizard until the
tenant has chosen a base currency and at least one Account.

HTMX: all tab-bodies (Daybook / Income & Expenses / Balance) are rendered as
partial templates that are also valid full pages, so a missing `HX-Request`
header still works.
"""
from __future__ import annotations

from datetime import date as date_cls
from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounting.forms import (
    AccountForm,
    BankStatementUploadForm,
    BaseCurrencyForm,
    DaybookFilterForm,
    EndingBalanceForm,
)
from apps.accounting.models import FiscalPeriod, PeriodAccountBalance
from apps.accounting.services.balance import (
    recompute_period_balances,
    set_reported_ending_balance,
)
from apps.accounting.services.daybook import (
    build_daybook,
    daybook_with_running_balance,
)
from apps.accounting.services.exports import (
    build_workbook_response,
    build_yearly_workbook_response,
)
from apps.accounting.services.income_statement import build_income_statement
from apps.accounting.services.monthly_close import (
    PeriodNotBalancedError,
    close_period,
    reopen_period,
)
from apps.accounting.services.period import (
    current_period,
    get_or_create_period,
    list_periods,
    period_date_range,
)
from apps.accounting.setup import (
    accounting_setup_required,
    get_base_currency,
    is_setup_completed,
    mark_setup_completed,
    setup_steps,
)
from apps.documents.models import DocumentFile, DocumentFolder
from apps.money.models import Account, Transaction
from apps.money.services.bank_import import import_bank_statement
from apps.money.services.reconciliation import auto_match_lines


# ---------------------------------------------------------------------------
# Setup wizard
# ---------------------------------------------------------------------------


@login_required
def setup_intro(request: HttpRequest) -> HttpResponse:
    if is_setup_completed(request):
        return redirect("accounting:dashboard")
    return render(
        request,
        "accounting/setup/intro.html",
        {"steps": list(setup_steps()), "current_step": "intro"},
    )


@login_required
@require_http_methods(["GET", "POST"])
def setup_currency(request: HttpRequest) -> HttpResponse:
    initial = {"currency": None}
    if getattr(request, "tenant", None) and request.tenant.currency:
        from apps.money.models import Currency

        initial["currency"] = (
            Currency.objects.filter(code=request.tenant.currency).first()
        )

    form = BaseCurrencyForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        currency = form.cleaned_data["currency"]
        tenant = request.tenant
        tenant.currency = currency.code
        tenant.save(update_fields=["currency"])
        messages.success(request, f"Base currency set to {currency.code}.")
        return redirect("accounting:setup_accounts")

    return render(
        request,
        "accounting/setup/currency.html",
        {
            "form": form,
            "steps": list(setup_steps()),
            "current_step": "currency",
            "current_currency": get_base_currency(request),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def setup_accounts(request: HttpRequest) -> HttpResponse:
    form = AccountForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Account added.")
        return redirect("accounting:setup_accounts")

    return render(
        request,
        "accounting/setup/accounts.html",
        {
            "form": form,
            "accounts": Account.objects.filter(is_active=True).order_by("kind", "name"),
            "steps": list(setup_steps()),
            "current_step": "accounts",
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def setup_review(request: HttpRequest) -> HttpResponse:
    accounts = Account.objects.filter(is_active=True).order_by("kind", "name")
    has_account = accounts.exists()

    if request.method == "POST":
        if not has_account:
            messages.error(request, "Add at least one account before completing setup.")
            return redirect("accounting:setup_accounts")
        mark_setup_completed(request)
        messages.success(request, "Accounting setup completed.")
        return redirect("accounting:dashboard")

    return render(
        request,
        "accounting/setup/review.html",
        {
            "accounts": accounts,
            "currency": get_base_currency(request),
            "has_account": has_account,
            "steps": list(setup_steps()),
            "current_step": "review",
        },
    )


# ---------------------------------------------------------------------------
# Dashboard / period detail
# ---------------------------------------------------------------------------


@accounting_setup_required
def dashboard(request: HttpRequest) -> HttpResponse:
    today = timezone.localdate()
    period = current_period(today)
    recompute_period_balances(period)
    balances = (
        PeriodAccountBalance.objects.filter(period=period)
        .select_related("account", "account__currency")
        .order_by("account__name")
    )
    return render(
        request,
        "accounting/dashboard.html",
        {
            "period": period,
            "balances": balances,
            "today": today,
            "base_currency": get_base_currency(request),
            "recent_periods": list_periods(limit=6),
        },
    )


@accounting_setup_required
def period_list(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "accounting/period_list.html",
        {"periods": list(list_periods(limit=36))},
    )


@accounting_setup_required
def period_detail(request: HttpRequest, year: int, month: int) -> HttpResponse:
    period = get_or_create_period(year, month)
    recompute_period_balances(period)
    balances = (
        PeriodAccountBalance.objects.filter(period=period)
        .select_related("account", "account__currency")
        .order_by("account__name")
    )
    date_from, date_to = period_date_range(period)
    transaction_count = Transaction.objects.filter(
        date__gte=date_from, date__lte=date_to
    ).count()
    return render(
        request,
        "accounting/period_detail.html",
        {
            "period": period,
            "balances": balances,
            "transaction_count": transaction_count,
            "active_tab": "daybook",
        },
    )


# ---------------------------------------------------------------------------
# HTMX tab bodies
# ---------------------------------------------------------------------------


def _wants_partial(request: HttpRequest) -> bool:
    return request.headers.get("HX-Request") == "true"


@accounting_setup_required
def period_daybook(request: HttpRequest, year: int, month: int) -> HttpResponse:
    period = get_or_create_period(year, month)
    date_from, date_to = period_date_range(period)
    qs = build_daybook(date_from=date_from, date_to=date_to)
    rows = daybook_with_running_balance(list(qs))
    template = (
        "accounting/partials/_daybook_table.html"
        if _wants_partial(request)
        else "accounting/period_daybook.html"
    )
    return render(
        request,
        template,
        {
            "period": period,
            "rows": rows,
            "active_tab": "daybook",
        },
    )


@accounting_setup_required
def period_income_statement(
    request: HttpRequest, year: int, month: int
) -> HttpResponse:
    period = get_or_create_period(year, month)
    summary = build_income_statement(period)
    template = (
        "accounting/partials/_income_statement.html"
        if _wants_partial(request)
        else "accounting/period_income_statement.html"
    )
    return render(
        request,
        template,
        {
            "period": period,
            "summary": summary,
            "active_tab": "income_statement",
        },
    )


@accounting_setup_required
def period_balance(request: HttpRequest, year: int, month: int) -> HttpResponse:
    period = get_or_create_period(year, month)
    recompute_period_balances(period)
    balances = (
        PeriodAccountBalance.objects.filter(period=period)
        .select_related("account", "account__currency")
        .order_by("account__name")
    )
    template = (
        "accounting/partials/_balance.html"
        if _wants_partial(request)
        else "accounting/period_balance.html"
    )
    return render(
        request,
        template,
        {
            "period": period,
            "balances": balances,
            "active_tab": "balance",
        },
    )


# ---------------------------------------------------------------------------
# Filterable Daybook (cross-period)
# ---------------------------------------------------------------------------


@accounting_setup_required
def daybook(request: HttpRequest) -> HttpResponse:
    today = timezone.localdate()
    default_from = today.replace(day=1)
    form = DaybookFilterForm(
        request.GET or None,
        initial={"date_from": default_from, "date_to": today},
    )
    rows: list = []
    if form.is_valid() or not request.GET:
        cleaned = form.cleaned_data if form.is_valid() else {}
        date_from = cleaned.get("date_from") or default_from
        date_to = cleaned.get("date_to") or today
        account = cleaned.get("account")
        direction = cleaned.get("direction") or None
        qs = build_daybook(
            date_from=date_from,
            date_to=date_to,
            account_id=account.id if account else None,
            direction=direction,
        )
        rows = daybook_with_running_balance(list(qs))

    template = (
        "accounting/partials/_daybook_filter_table.html"
        if _wants_partial(request)
        else "accounting/daybook.html"
    )
    return render(
        request,
        template,
        {"form": form, "rows": rows},
    )


# ---------------------------------------------------------------------------
# Mutations: ending balance + period close
# ---------------------------------------------------------------------------


@accounting_setup_required
@require_http_methods(["POST"])
def set_ending_balance(
    request: HttpRequest, year: int, month: int, account_id: int
) -> HttpResponse:
    period = get_or_create_period(year, month)
    if period.is_locked:
        return HttpResponseBadRequest("Period is locked.")
    account = get_object_or_404(Account, pk=account_id, is_active=True)

    raw_ending = request.POST.get("ending_balance", "").strip()
    try:
        ending = Decimal(raw_ending) if raw_ending else Decimal("0")
    except InvalidOperation:
        return HttpResponseBadRequest("Invalid amount.")

    set_reported_ending_balance(period, account, ending)
    if _wants_partial(request):
        return period_balance(request, year, month)
    messages.success(request, f"Saved ending balance for {account.name}.")
    return redirect("accounting:period_detail", year=year, month=month)


@accounting_setup_required
@require_http_methods(["POST"])
def close_period_view(request: HttpRequest, year: int, month: int) -> HttpResponse:
    period = get_or_create_period(year, month)
    force = request.POST.get("force") == "1"
    try:
        close_period(period, user=request.user, force=force)
    except PeriodNotBalancedError as exc:
        messages.error(request, str(exc))
        return redirect("accounting:period_detail", year=year, month=month)
    messages.success(request, f"Period {period.label} closed.")
    return redirect("accounting:period_detail", year=year, month=month)


@accounting_setup_required
@require_http_methods(["POST"])
def reopen_period_view(request: HttpRequest, year: int, month: int) -> HttpResponse:
    period = get_or_create_period(year, month)
    reopen_period(period)
    messages.success(request, f"Period {period.label} reopened.")
    return redirect("accounting:period_detail", year=year, month=month)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


@accounting_setup_required
def export_period(request: HttpRequest, year: int, month: int) -> HttpResponse:
    period = get_or_create_period(year, month)
    return build_workbook_response(period, user=request.user)


@accounting_setup_required
def export_year(request: HttpRequest, year: int) -> HttpResponse:
    """Calendar-year XLSX (Jan–Dec) for the accountant."""
    return build_yearly_workbook_response(year, user=request.user)


# ---------------------------------------------------------------------------
# Bank statement upload
# ---------------------------------------------------------------------------


@accounting_setup_required
@require_http_methods(["GET", "POST"])
def import_bank_statement_view(request: HttpRequest) -> HttpResponse:
    form = BankStatementUploadForm(request.POST or None, request.FILES or None)
    statement = None
    stats = None

    if request.method == "POST" and form.is_valid():
        upload = form.cleaned_data["file"]
        account = form.cleaned_data["account"]
        max_bytes = getattr(settings, "INVOICE_MAX_UPLOAD_BYTES", 25 * 1024 * 1024)
        if upload.size > max_bytes:
            form.add_error(
                "file",
                f"File exceeds maximum upload size ({max_bytes} bytes).",
            )
        else:
            folder, _ = DocumentFolder.objects.get_or_create(
                path="bank-statements", defaults={"name": "Bank statements"}
            )
            document = DocumentFile(
                folder=folder,
                filename=upload.name,
                file_path="",
                file_type=upload.name.rsplit(".", 1)[-1].lower(),
                status="pending",
            )
            document.file.save(upload.name, upload, save=False)
            document.recompute_file_metadata()
            document.save()
            statement = import_bank_statement(account=account, document=document)
            stats = auto_match_lines(statement)
            messages.success(
                request,
                f"Imported {statement.lines.count()} lines, {stats['matched']} matched automatically.",
            )

    return render(
        request,
        "accounting/import_bank_statement.html",
        {"form": form, "statement": statement, "stats": stats},
    )
