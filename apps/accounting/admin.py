"""Admin registration for accounting models.

The `Daybook` proxy provides a per-month, multi-account inspectable view that
composes invoices and transactions through `period_feed.build_period_feed`.
The view is read-mostly: it renders four sections (header, openings, lines,
closings) and exposes per-row actions to confirm opening balances and
recompute a period.
"""
from __future__ import annotations

from decimal import Decimal

from django.contrib import admin, messages
from django.db.models import Count, Q, Sum
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from apps.accounting.models import (
    AccountingExport,
    Daybook,
    FiscalPeriod,
    PeriodAccountBalance,
)
from apps.accounting.services.balance import (
    confirm_opening_balance,
    recompute_period_balances,
    set_reported_ending_balance,
)
from apps.accounting.services.period_feed import build_period_feed
from apps.core.admin_changelist import ChangelistMetricsMixin
from apps.core.admin_mixins import TenantSchemaOnlyAdminMixin
from apps.money.models import Account


class PeriodAccountBalanceInline(TabularInline):
    model = PeriodAccountBalance
    extra = 0
    fields = (
        "account",
        "starting_balance",
        "computed_flow",
        "computed_ending",
        "ending_balance",
        "discrepancy",
        "is_balanced",
    )
    readonly_fields = ("computed_flow", "computed_ending", "discrepancy", "is_balanced")
    raw_id_fields = ("account",)


@admin.register(FiscalPeriod)
class FiscalPeriodAdmin(TenantSchemaOnlyAdminMixin, ChangelistMetricsMixin, ModelAdmin):
    list_display = ("label", "status", "closed_at", "closed_by")
    list_filter = ("status", "year")
    search_fields = ("notes",)
    inlines = [PeriodAccountBalanceInline]

    def get_changelist_metrics(self, request, queryset):
        return [
            {"label": "Periods", "value": queryset.count()},
            {
                "label": "Open",
                "value": queryset.filter(status="open").count(),
                "help": "Editable periods that are not closed.",
            },
            {
                "label": "Closed",
                "value": queryset.filter(status="closed").count(),
                "help": "Closed and ready for audit/export.",
            },
            {
                "label": "Locked",
                "value": queryset.filter(status="locked").count(),
                "help": "Finalized periods protected from changes.",
            },
        ]


@admin.register(PeriodAccountBalance)
class PeriodAccountBalanceAdmin(TenantSchemaOnlyAdminMixin, ChangelistMetricsMixin, ModelAdmin):
    list_display = (
        "period",
        "account",
        "starting_balance",
        "computed_ending",
        "ending_balance",
        "discrepancy",
        "is_balanced",
    )
    list_filter = ("is_balanced", "period")
    raw_id_fields = ("period", "account")
    readonly_fields = ("computed_flow", "computed_ending", "discrepancy", "is_balanced")

    def get_changelist_metrics(self, request, queryset):
        matched = queryset.filter(is_balanced=True).count()
        total = queryset.count()
        mismatched = total - matched
        return [
            {"label": "Account checks", "value": total},
            {"label": "Balanced", "value": matched},
            {
                "label": "Mismatches",
                "value": mismatched,
                "help": "Rows where ending and computed balances differ.",
            },
            {
                "label": "Mismatch rate",
                "value": f"{((mismatched / total) * 100):.1f}%" if total else "0.0%",
            },
        ]


@admin.register(AccountingExport)
class AccountingExportAdmin(TenantSchemaOnlyAdminMixin, ModelAdmin):
    list_display = ("kind", "period", "generated_at", "generated_by", "file_name")
    list_filter = ("kind",)
    raw_id_fields = ("period", "generated_by")
    readonly_fields = ("generated_at",)


# ---------------------------------------------------------------------------
# Daybook (proxy of FiscalPeriod) -- the inspectable monthly view
# ---------------------------------------------------------------------------


@admin.register(Daybook)
class DaybookAdmin(TenantSchemaOnlyAdminMixin, ChangelistMetricsMixin, ModelAdmin):
    """Inspectable monthly daybook across every account.

    Changelist: one row per FiscalPeriod with annotated totals and a
    balanced-or-not flag. The change view is fully custom: instead of a
    standard form it renders the daybook feed and lets the user confirm
    opening balances per account, save reported ending balances, recompute,
    close/reopen, and export.
    """

    change_form_template = "admin/accounting/daybook/change_form.html"
    list_display = (
        "label",
        "status",
        "account_count",
        "total_in",
        "total_out",
        "total_closing",
        "balanced_flag",
    )
    list_filter = ("status", "year")
    search_fields = ("notes",)
    actions = ["recompute_selected"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _account_count=Count("balances", distinct=True),
            _total_starting=Sum("balances__starting_balance"),
            _total_closing=Sum("balances__computed_ending"),
            _total_discrepancy=Sum("balances__discrepancy"),
            _unbalanced_count=Count(
                "balances", filter=Q(balances__is_balanced=False), distinct=True
            ),
        )

    @admin.display(description="Accounts", ordering="_account_count")
    def account_count(self, obj):
        return obj._account_count or 0

    @admin.display(description="Total closing", ordering="_total_closing")
    def total_closing(self, obj):
        return obj._total_closing or Decimal("0")

    @admin.display(description="In", ordering="_total_starting")
    def total_in(self, obj):
        feed = build_period_feed(obj)
        return feed.totals.get("total_in") or Decimal("0")

    @admin.display(description="Out")
    def total_out(self, obj):
        feed = build_period_feed(obj)
        return feed.totals.get("total_out") or Decimal("0")

    @admin.display(description="Balanced")
    def balanced_flag(self, obj):
        unbalanced = obj._unbalanced_count or 0
        if (obj._account_count or 0) == 0:
            return format_html('<span class="text-base-500">no accounts</span>')
        if unbalanced == 0:
            return format_html('<span class="text-green-600">OK</span>')
        return format_html(
            '<span class="text-red-600">{} mismatch{}</span>',
            unbalanced,
            "" if unbalanced == 1 else "es",
        )

    def get_changelist_metrics(self, request, queryset):
        total = queryset.count()
        open_count = queryset.filter(status=FiscalPeriod.STATUS_OPEN).count()
        closed_count = queryset.filter(status=FiscalPeriod.STATUS_CLOSED).count()
        return [
            {"label": "Daybooks", "value": total},
            {"label": "Open", "value": open_count},
            {"label": "Closed", "value": closed_count},
        ]

    @admin.action(description="Recompute selected daybooks")
    def recompute_selected(self, request, queryset):
        for period in queryset:
            recompute_period_balances(period)
        self.message_user(
            request,
            f"Recomputed {queryset.count()} daybook(s).",
            messages.SUCCESS,
        )

    # -----------------------------------------------------------------
    # URLs and custom views
    # -----------------------------------------------------------------

    def get_urls(self):
        urls = super().get_urls()
        opts = self.model._meta
        prefix = f"{opts.app_label}_{opts.model_name}"
        custom = [
            path(
                "<int:object_id>/confirm-opening/<int:account_id>/",
                self.admin_site.admin_view(self.confirm_opening_view),
                name=f"{prefix}_confirm_opening",
            ),
            path(
                "<int:object_id>/save-ending/<int:account_id>/",
                self.admin_site.admin_view(self.save_ending_view),
                name=f"{prefix}_save_ending",
            ),
            path(
                "<int:object_id>/recompute/",
                self.admin_site.admin_view(self.recompute_view),
                name=f"{prefix}_recompute",
            ),
        ]
        return custom + urls

    def change_view(self, request, object_id, form_url="", extra_context=None):
        period = get_object_or_404(Daybook, pk=object_id)
        recompute_period_balances(period)
        feed = build_period_feed(period)

        context = {
            **self.admin_site.each_context(request),
            "title": f"Daybook {period.label}",
            "opts": self.model._meta,
            "object_id": object_id,
            "original": period,
            "period": period,
            "feed": feed,
            "entries": feed.entries,
            "balances": list(feed.openings),
            "totals": feed.totals,
            "has_view_permission": self.has_view_permission(request, period),
            "has_change_permission": self.has_change_permission(request, period),
            "media": self.media,
            "is_popup": False,
            "save_as": False,
            "show_save": False,
            "show_save_and_continue": False,
            "show_save_and_add_another": False,
            "show_delete": False,
            "preserved_filters": self.get_preserved_filters(request),
            "url_confirm_opening": f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_confirm_opening",
            "url_save_ending": f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_save_ending",
            "url_recompute": f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_recompute",
        }
        if extra_context:
            context.update(extra_context)
        return TemplateResponse(request, self.change_form_template, context)

    def confirm_opening_view(self, request, object_id, account_id):
        if request.method != "POST":
            messages.error(request, "Method not allowed.")
            return HttpResponseRedirect(self._daybook_change_url(object_id))
        period = get_object_or_404(Daybook, pk=object_id)
        account = get_object_or_404(Account, pk=account_id)
        raw = (request.POST.get("starting_balance") or "").strip()
        try:
            starting = Decimal(raw) if raw else None
        except Exception:
            messages.error(request, "Invalid starting balance.")
            return HttpResponseRedirect(self._daybook_change_url(object_id))

        confirm_opening_balance(period, account, request.user, starting_balance=starting)
        messages.success(
            request,
            f"Opening balance for {account.name} confirmed.",
        )
        return HttpResponseRedirect(self._daybook_change_url(object_id))

    def save_ending_view(self, request, object_id, account_id):
        if request.method != "POST":
            messages.error(request, "Method not allowed.")
            return HttpResponseRedirect(self._daybook_change_url(object_id))
        period = get_object_or_404(Daybook, pk=object_id)
        if period.is_locked:
            messages.error(request, "Period is locked.")
            return HttpResponseRedirect(self._daybook_change_url(object_id))
        account = get_object_or_404(Account, pk=account_id)
        raw = (request.POST.get("ending_balance") or "").strip()
        try:
            ending = Decimal(raw) if raw else Decimal("0")
        except Exception:
            messages.error(request, "Invalid ending balance.")
            return HttpResponseRedirect(self._daybook_change_url(object_id))

        set_reported_ending_balance(period, account, ending)
        messages.success(
            request,
            f"Ending balance for {account.name} saved.",
        )
        return HttpResponseRedirect(self._daybook_change_url(object_id))

    def recompute_view(self, request, object_id):
        if request.method != "POST":
            messages.error(request, "Method not allowed.")
            return HttpResponseRedirect(self._daybook_change_url(object_id))
        period = get_object_or_404(Daybook, pk=object_id)
        recompute_period_balances(period)
        messages.success(
            request,
            f"Daybook {period.label} recomputed at {timezone.now():%Y-%m-%d %H:%M}.",
        )
        return HttpResponseRedirect(self._daybook_change_url(object_id))

    def _daybook_change_url(self, object_id):
        opts = self.model._meta
        return reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[object_id])
