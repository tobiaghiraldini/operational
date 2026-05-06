from django.contrib import admin
from django.db.models import Q, Sum
from unfold.admin import ModelAdmin, TabularInline

from apps.core.admin_changelist import ChangelistMetricsMixin
from apps.core.admin_mixins import TenantSchemaOnlyAdminMixin
from .models import (
    Account,
    BankStatement,
    BankStatementLine,
    Currency,
    ExchangeRate,
    Transaction,
    TransactionCategory,
)


@admin.register(Currency)
class CurrencyAdmin(TenantSchemaOnlyAdminMixin, ModelAdmin):
    list_display = ("code", "name", "symbol", "decimal_places", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(ExchangeRate)
class ExchangeRateAdmin(TenantSchemaOnlyAdminMixin, ModelAdmin):
    list_display = ("from_currency", "to_currency", "rate", "valid_from", "source")
    list_filter = ("source", "valid_from")
    raw_id_fields = ("from_currency", "to_currency")


@admin.register(Account)
class AccountAdmin(TenantSchemaOnlyAdminMixin, ModelAdmin):
    list_display = ("name", "kind", "currency", "iban", "bank_name", "is_active")
    list_filter = ("kind", "is_active", "currency")
    search_fields = ("name", "iban", "bank_name")


@admin.register(TransactionCategory)
class TransactionCategoryAdmin(TenantSchemaOnlyAdminMixin, ModelAdmin):
    list_display = ("name", "kind", "parent")
    list_filter = ("kind",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    raw_id_fields = ("parent",)


class BankStatementLineInline(TabularInline):
    model = BankStatementLine
    extra = 0
    fields = ("date", "direction", "amount", "description", "is_matched", "matched_transaction")
    readonly_fields = ("is_matched",)
    raw_id_fields = ("matched_transaction",)


@admin.register(BankStatement)
class BankStatementAdmin(TenantSchemaOnlyAdminMixin, ModelAdmin):
    list_display = (
        "account",
        "period_start",
        "period_end",
        "opening_balance",
        "closing_balance",
        "parse_status",
    )
    list_filter = ("parse_status", "account")
    date_hierarchy = "period_end"
    inlines = [BankStatementLineInline]
    raw_id_fields = ("account", "document")


@admin.register(Transaction)
class TransactionAdmin(TenantSchemaOnlyAdminMixin, ChangelistMetricsMixin, ModelAdmin):
    list_display = (
        "date",
        "direction",
        "amount",
        "currency",
        "account",
        "category",
        "counterparty",
        "invoice",
    )
    list_filter = ("direction", "category", "account", "currency", "date")
    search_fields = ("counterparty", "description", "reference")
    raw_id_fields = (
        "account",
        "category",
        "currency",
        "invoice",
        "customer",
        "vendor",
        "document",
        "bank_statement_line",
    )
    date_hierarchy = "date"

    def get_changelist_metrics(self, request, queryset):
        aggregates = queryset.aggregate(
            total=Sum("amount"),
            incoming=Sum("amount", filter=Q(direction="in")),
            outgoing=Sum("amount", filter=Q(direction="out")),
        )
        return [
            {"label": "Transactions", "value": queryset.count()},
            {
                "label": "Incoming",
                "value": f"{(aggregates['incoming'] or 0):.2f}",
                "help": "Sum of inbound money movements.",
            },
            {
                "label": "Outgoing",
                "value": f"{(aggregates['outgoing'] or 0):.2f}",
                "help": "Sum of outbound money movements.",
            },
            {
                "label": "Gross moved",
                "value": f"{(aggregates['total'] or 0):.2f}",
                "help": "Total absolute volume in current list scope.",
            },
        ]
