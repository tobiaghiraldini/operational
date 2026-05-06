"""django-import-export resources for tabular accounting data."""
from import_export import fields, resources
from import_export.widgets import (
    DateWidget,
    DecimalWidget,
    ForeignKeyWidget,
)

from apps.accounting.models import PeriodAccountBalance
from apps.money.models import Account, Currency, Transaction, TransactionCategory


class TransactionResource(resources.ModelResource):
    """Daybook-shaped Transaction import/export."""

    date = fields.Field(
        attribute="date", column_name="Date", widget=DateWidget(format="%Y-%m-%d")
    )
    direction = fields.Field(attribute="direction", column_name="Direction")
    amount = fields.Field(
        attribute="amount", column_name="Amount", widget=DecimalWidget()
    )
    currency = fields.Field(
        attribute="currency",
        column_name="Currency",
        widget=ForeignKeyWidget(Currency, field="code"),
    )
    account = fields.Field(
        attribute="account",
        column_name="Account",
        widget=ForeignKeyWidget(Account, field="name"),
    )
    category = fields.Field(
        attribute="category",
        column_name="Category",
        widget=ForeignKeyWidget(TransactionCategory, field="slug"),
    )
    counterparty = fields.Field(attribute="counterparty", column_name="Counterparty")
    description = fields.Field(attribute="description", column_name="Description")
    reference = fields.Field(attribute="reference", column_name="Reference")

    class Meta:
        model = Transaction
        fields = (
            "id",
            "date",
            "direction",
            "amount",
            "currency",
            "account",
            "category",
            "counterparty",
            "description",
            "reference",
        )
        export_order = fields
        skip_unchanged = True
        report_skipped = False


class PeriodAccountBalanceResource(resources.ModelResource):
    """Export only -- per-account closing reconciliation per period."""

    period_label = fields.Field(column_name="Period")
    account_name = fields.Field(column_name="Account")
    starting_balance = fields.Field(
        attribute="starting_balance", column_name="Opening", widget=DecimalWidget()
    )
    computed_flow = fields.Field(
        attribute="computed_flow", column_name="Flow", widget=DecimalWidget()
    )
    computed_ending = fields.Field(
        attribute="computed_ending",
        column_name="Computed closing",
        widget=DecimalWidget(),
    )
    ending_balance = fields.Field(
        attribute="ending_balance",
        column_name="Reported closing",
        widget=DecimalWidget(),
    )
    discrepancy = fields.Field(
        attribute="discrepancy", column_name="Discrepancy", widget=DecimalWidget()
    )
    is_balanced = fields.Field(attribute="is_balanced", column_name="Balanced")

    class Meta:
        model = PeriodAccountBalance
        fields = (
            "period_label",
            "account_name",
            "starting_balance",
            "computed_flow",
            "computed_ending",
            "ending_balance",
            "discrepancy",
            "is_balanced",
        )
        export_order = fields

    def dehydrate_period_label(self, obj: PeriodAccountBalance) -> str:
        return obj.period.label if obj.period_id else ""

    def dehydrate_account_name(self, obj: PeriodAccountBalance) -> str:
        return obj.account.name if obj.account_id else ""
