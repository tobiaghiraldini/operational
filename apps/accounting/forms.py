"""Forms for the accounting setup wizard, period editing, and bank import."""
from __future__ import annotations

from django import forms

from apps.money.models import Account, Currency


class BaseCurrencyForm(forms.Form):
    currency = forms.ModelChoiceField(
        queryset=Currency.objects.filter(is_active=True).order_by("code"),
        empty_label=None,
        help_text="Base currency reported on every accounting export.",
    )


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = (
            "name",
            "kind",
            "currency",
            "iban",
            "bank_name",
            "opening_balance",
            "opening_date",
            "notes",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["currency"].queryset = Currency.objects.filter(is_active=True)


class EndingBalanceForm(forms.Form):
    account_id = forms.IntegerField(widget=forms.HiddenInput)
    ending_balance = forms.DecimalField(max_digits=14, decimal_places=2)


class CloseSearchForm(forms.Form):
    force = forms.BooleanField(required=False, help_text="Close even if not balanced.")


class BankStatementUploadForm(forms.Form):
    account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_active=True), empty_label=None
    )
    file = forms.FileField(help_text="Upload the bank statement PDF.")


class DaybookFilterForm(forms.Form):
    date_from = forms.DateField(required=False)
    date_to = forms.DateField(required=False)
    account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_active=True),
        required=False,
    )
    direction = forms.ChoiceField(
        required=False,
        choices=(("", "All"), ("in", "In"), ("out", "Out")),
    )
