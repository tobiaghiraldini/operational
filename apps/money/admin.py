from django.contrib import admin
from django.db.models import Q, Sum
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from apps.core.admin_changelist import ChangelistMetricsMixin
from apps.core.admin_mixins import (
    SettlementAllocationUsesParentPermissionsMixin,
    TenantSchemaOnlyAdminMixin,
)
from apps.money.forms.invoice_settlement_allocation_admin import (
    InvoiceSettlementAllocationAdminForm,
)
from apps.money.forms.transaction_settlement_allocation_formset import (
    TransactionSettlementAllocationFormSet,
)
from .models import (
    Account,
    BankStatement,
    BankStatementLine,
    Currency,
    ExchangeRate,
    InvoiceSettlementAllocation,
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
    list_display = ("name", "kind", "currency", "iban", "bank_name", "is_active", "is_default")
    list_filter = ("kind", "is_active", "is_default", "currency")
    search_fields = ("name", "iban", "bank_name")


@admin.register(TransactionCategory)
class TransactionCategoryAdmin(TenantSchemaOnlyAdminMixin, ModelAdmin):
    list_display = ("name", "kind", "parent")
    list_filter = ("kind",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    raw_id_fields = ("parent",)


class InvoiceSettlementAllocationInline(
    SettlementAllocationUsesParentPermissionsMixin, TabularInline
):
    model = InvoiceSettlementAllocation
    form = InvoiceSettlementAllocationAdminForm
    tab = True
    verbose_name = "Bank settlement line"
    verbose_name_plural = "Bank settlement lines"
    extra = 0
    autocomplete_fields = ("invoice",)
    fields = (
        "invoice",
        "amount_settlement",
        "amount_invoice",
        "fx_rate",
        "notes",
    )


class TransactionSettlementAllocationInline(InvoiceSettlementAllocationInline):
    """Fills one fee-only row (blank settlement) with the bank-line remainder."""

    formset = TransactionSettlementAllocationFormSet


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


@admin.register(BankStatementLine)
class BankStatementLineAdmin(TenantSchemaOnlyAdminMixin, ModelAdmin):
    """Standalone registration so Transaction FK autocomplete can resolve this model."""

    list_display = ("date", "direction", "amount", "statement", "description")
    list_filter = ("direction", "date")
    search_fields = (
        "description",
        "bank_reference",
        "statement__account__name",
    )
    raw_id_fields = ("statement",)


@admin.register(InvoiceSettlementAllocation)
class InvoiceSettlementAllocationAdmin(TenantSchemaOnlyAdminMixin, ModelAdmin):
    form = InvoiceSettlementAllocationAdminForm
    list_display = (
        "transaction",
        "invoice",
        "amount_settlement",
        "amount_invoice",
        "created_at",
    )
    list_filter = ("transaction__date",)
    search_fields = (
        "invoice__invoice_number",
        "transaction__reference",
        "transaction__description",
        "transaction__counterparty",
    )
    autocomplete_fields = ("invoice", "transaction")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Transaction)
class TransactionAdmin(TenantSchemaOnlyAdminMixin, ChangelistMetricsMixin, ModelAdmin):
    change_form_template = "admin/unfold_changeform_include_inlines.html"
    list_display = (
        "date",
        "amount_display",
        "currency",
        "account",
        "category",
        "counterparty",
        "linked_invoices_display",
        "allocation_gap_display",
    )
    list_filter = ("direction", "category", "account", "currency", "date")
    search_fields = (
        "counterparty",
        "description",
        "reference",
        "account__name",
        "account__iban",
        "vendor__name",
        "customer__name",
    )
    autocomplete_fields = (
        "account",
        "category",
        "currency",
        "customer",
        "vendor",
        "document",
        "bank_statement_line",
    )
    date_hierarchy = "date"
    inlines = [TransactionSettlementAllocationInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("account", "currency", "category")

    def linked_invoices_display(self, obj):
        from apps.money.services.invoice_document_label import (
            transaction_invoice_document_label,
        )

        return transaction_invoice_document_label(obj) or "—"

    linked_invoices_display.short_description = "Invoices"

    def allocation_gap_display(self, obj):
        gap = obj.settlement_allocation_gap()
        if gap == 0:
            return "0"
        return f"{gap:.2f}"

    allocation_gap_display.short_description = "Alloc. gap"
    allocation_gap_display.admin_order_by = None

    def amount_display(self, obj):
        """In: + green; out: − red (same colors/fonts as invoice amounts)."""
        if obj.amount is None:
            return "—"
        amount_str = f"{obj.amount:.2f}"
        if obj.direction == Transaction.DIRECTION_IN:
            return format_html(
                '<span style="color: #16a34a; font-variant-numeric: tabular-nums;">+{}</span>',
                amount_str,
            )
        return format_html(
            '<span style="color: #dc2626; font-variant-numeric: tabular-nums;">-{}</span>',
            amount_str,
        )

    amount_display.short_description = "Amount"
    amount_display.admin_order_by = "amount"

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
