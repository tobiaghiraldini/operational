from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.core.admin_changelist import ChangelistMetricsMixin
from apps.core.admin_mixins import TenantSchemaOnlyAdminMixin
from .models import AccountingExport, FiscalPeriod, PeriodAccountBalance


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
