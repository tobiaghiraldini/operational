from django.contrib import admin
from django.contrib.admin.widgets import AutocompleteSelect
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from apps.core.admin_mixins import (
    SettlementAllocationUsesParentPermissionsMixin,
    TenantSchemaOnlyAdminMixin,
)
from apps.money.forms.invoice_settlement_allocation_admin import (
    InvoiceSettlementAllocationAdminForm,
)
from apps.money.forms.settlement_allocation_inline_formset import (
    SettlementAllocationInlineFormSet,
)
from apps.money.models import InvoiceSettlementAllocation

from .models import Invoice, InvoiceExtraction


class InvoiceExtractionInline(admin.StackedInline):
    model = InvoiceExtraction
    extra = 0
    readonly_fields = ['created_at', 'updated_at', 'processed_at', 'retry_count']
    fields = [
        'extraction_method', 'confidence_score', 'field_confidence', 'llm_model_name',
        'prompt_version', 'processed_at',
        'raw_extracted_data', 'validated_data', 'retry_count', 'last_error'
    ]


class InvoiceSettlementAllocationInline(
    SettlementAllocationUsesParentPermissionsMixin, TabularInline
):
    """Link this invoice to bank/cash transactions (e.g. card statement batch)."""

    model = InvoiceSettlementAllocation
    form = InvoiceSettlementAllocationAdminForm
    formset = SettlementAllocationInlineFormSet
    verbose_name = "Bank settlement line"
    verbose_name_plural = "Bank settlement lines"
    extra = 0
    classes = ("invoice-financial-settlement-inline",)
    autocomplete_fields = ("transaction",)
    fields = (
        "transaction",
        "amount_settlement",
        "amount_invoice",
        "notes",
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "transaction":
            kwargs["widget"] = AutocompleteSelect(
                db_field,
                self.admin_site,
                using=kwargs.get("using"),
                attrs={
                    "style": "min-width: min(40rem, 100%); max-width: 56rem; width: 100%;",
                    "class": "invoice-settlement-tx-autocomplete",
                },
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Invoice)
class InvoiceAdmin(TenantSchemaOnlyAdminMixin, ModelAdmin):
    change_form_template = "admin/invoices/invoice/change_form.html"
    list_display = [
        'invoice_number', 'vendor', 'customer', 'invoice_date', 'due_date',
        'total_amount_display', 'currency', 'invoice_type', 'status',
        'is_paid_display', 'days_overdue_display'
    ]
    list_filter = [
        'status', 'invoice_type', 'currency', 'vendor', 'payment_method', 
        'invoice_date', 'due_date', 'payment_date', 'created_at', 'template'
    ]
    search_fields = ['invoice_number', 'vendor__name', 'original_filename', 'document_file__filename']
    readonly_fields = [
        'created_at', 'updated_at', 'file_size', 'is_paid_display', 
        'days_overdue_display', 'file_path_display'
    ]
    date_hierarchy = 'invoice_date'
    
    fieldsets = (
        ('Invoice Information', {
            'fields': (
                'invoice_number', 'invoice_date', 'due_date', 'payment_date',
                'status', 'needs_manual_review'
            )
        }),
        ('Financial Information', {
            'fields': (
                'total_amount', 'currency', 'converted_amount', 'exchange_rate',
                'vat_percentage', 'vat_amount', 'taxable_amount'
            )
        }),
        ('Vendor & Payment', {
            'fields': (
                'vendor', 'customer', 'payment_method', 'invoice_type', 'document_kind',
                'classification_hints', 'template',
            )
        }),
        ('File Information', {
            'fields': (
                'document_file', 'original_filename', 'file_path_display', 'file_size',
                'extraction_errors'
            )
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [InvoiceExtractionInline, InvoiceSettlementAllocationInline]

    class Media:
        css = {"all": ("admin/css/invoice_financial_settlement.css",)}

    def total_amount_display(self, obj):
        """Emitted = income (+, green); received = expense (−, red)."""
        if obj.total_amount is None:
            return "—"
        amount_str = f"{obj.total_amount:.2f}"
        if obj.invoice_type == "emitted":
            return format_html(
                '<span style="color: #16a34a; font-variant-numeric: tabular-nums;">+{}</span>',
                amount_str,
            )
        return format_html(
            '<span style="color: #dc2626; font-variant-numeric: tabular-nums;">-{}</span>',
            amount_str,
        )

    total_amount_display.short_description = "Total amount"
    total_amount_display.admin_order_by = "total_amount"

    def is_paid_display(self, obj):
        if obj.is_paid:
            return format_html('<span style="color: green;">{} Paid</span>', "✓")
        else:
            return format_html('<span style="color: red;">{} Unpaid</span>', "✗")
    is_paid_display.short_description = 'Payment Status'
    
    def days_overdue_display(self, obj):
        days = obj.days_overdue
        if days is None:
            return format_html('<span style="color: orange;">{}</span>', "No due date")
        elif days > 0:
            return format_html('<span style="color: red;">{} days overdue</span>', days)
        elif days == 0:
            return format_html('<span style="color: orange;">{}</span>', "Due today")
        else:
            return format_html('<span style="color: green;">{} days remaining</span>', abs(days))
    days_overdue_display.short_description = 'Due Status'
    
    def file_path_display(self, obj):
        if obj.file_path:
            return format_html(
                '<a href="file://{}" target="_blank">{}</a>',
                obj.file_path,
                obj.original_filename
            )
        return '-'
    file_path_display.short_description = 'File'
    
    actions = ['mark_for_review', 'mark_completed', 'retry_extraction']
    
    def mark_for_review(self, request, queryset):
        updated = queryset.update(needs_manual_review=True, status='review')
        self.message_user(request, f'{updated} invoices marked for review.')
    mark_for_review.short_description = 'Mark selected invoices for review'
    
    def mark_completed(self, request, queryset):
        updated = queryset.update(status='completed', needs_manual_review=False)
        self.message_user(request, f'{updated} invoices marked as completed.')
    mark_completed.short_description = 'Mark selected invoices as completed'
    
    def retry_extraction(self, request, queryset):
        from django.db import connection
        from django_tenants.utils import get_public_schema_name

        from .tasks import process_single_invoice

        schema_name = (
            None
            if connection.schema_name == get_public_schema_name()
            else connection.schema_name
        )
        count = 0
        for invoice in queryset:
            process_single_invoice.delay(
                invoice.file_path,
                invoice.original_filename,
                document_file_id=invoice.document_file_id,
                schema_name=schema_name,
            )
            count += 1
        self.message_user(request, f'{count} invoices queued for re-extraction.')
    retry_extraction.short_description = 'Retry extraction for selected invoices'


@admin.register(InvoiceExtraction)
class InvoiceExtractionAdmin(TenantSchemaOnlyAdminMixin, admin.ModelAdmin):
    list_display = [
        'invoice', 'extraction_method', 'confidence_score', 
        'processed_at', 'retry_count'
    ]
    list_filter = ['extraction_method', 'processed_at', 'retry_count']
    search_fields = ['invoice__invoice_number', 'invoice__vendor__name']
    readonly_fields = ['created_at', 'updated_at', 'processed_at']
    
    fieldsets = (
        ('Extraction Information', {
            'fields': (
                'invoice', 'extraction_method', 'confidence_score', 'field_confidence',
                'llm_model_name', 'prompt_version',
                'processed_at', 'retry_count'
            )
        }),
        ('Raw Data', {
            'fields': ('raw_text', 'raw_extracted_data'),
            'classes': ('collapse',)
        }),
        ('Validated Data', {
            'fields': ('validated_data',),
            'classes': ('collapse',)
        }),
        ('Error Information', {
            'fields': ('last_error',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )