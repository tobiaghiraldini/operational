"""django-import-export resources for tabular invoice import/export."""
from import_export import fields, resources
from import_export.widgets import (
    DateWidget,
    DecimalWidget,
    ForeignKeyWidget,
)

from apps.customers.models import Customer
from apps.invoices.models import Invoice
from apps.vendors.models import Vendor


class InvoiceResource(resources.ModelResource):
    """Import/export issued and received invoices as a flat sheet."""

    invoice_number = fields.Field(attribute="invoice_number", column_name="Invoice #")
    invoice_type = fields.Field(attribute="invoice_type", column_name="Type")
    invoice_date = fields.Field(
        attribute="invoice_date",
        column_name="Date",
        widget=DateWidget(format="%Y-%m-%d"),
    )
    due_date = fields.Field(
        attribute="due_date",
        column_name="Due date",
        widget=DateWidget(format="%Y-%m-%d"),
    )
    payment_date = fields.Field(
        attribute="payment_date",
        column_name="Paid on",
        widget=DateWidget(format="%Y-%m-%d"),
    )
    customer = fields.Field(
        attribute="customer",
        column_name="Customer",
        widget=ForeignKeyWidget(Customer, field="name"),
    )
    vendor = fields.Field(
        attribute="vendor",
        column_name="Vendor",
        widget=ForeignKeyWidget(Vendor, field="name"),
    )
    taxable_amount = fields.Field(
        attribute="taxable_amount",
        column_name="Net",
        widget=DecimalWidget(),
    )
    vat_amount = fields.Field(
        attribute="vat_amount",
        column_name="VAT",
        widget=DecimalWidget(),
    )
    total_amount = fields.Field(
        attribute="total_amount",
        column_name="Gross",
        widget=DecimalWidget(),
    )
    currency = fields.Field(attribute="currency", column_name="Currency")
    status = fields.Field(attribute="status", column_name="Status")

    class Meta:
        model = Invoice
        fields = (
            "id",
            "invoice_number",
            "invoice_type",
            "invoice_date",
            "due_date",
            "payment_date",
            "customer",
            "vendor",
            "taxable_amount",
            "vat_amount",
            "total_amount",
            "currency",
            "status",
        )
        export_order = fields
        skip_unchanged = True
        report_skipped = False
