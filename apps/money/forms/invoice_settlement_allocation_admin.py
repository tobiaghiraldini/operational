"""Admin ModelForm: optional amounts; invoice lines use FX rates; fee lines omit invoice."""
from __future__ import annotations

from decimal import Decimal

from django import forms

from apps.money.models import InvoiceSettlementAllocation
from apps.money.services.settlement_conversion import amount_in_transaction_currency


class InvoiceSettlementAllocationAdminForm(forms.ModelForm):
    """Pick invoice + transaction (or a fee-only row on the transaction) — amounts default."""

    class Meta:
        model = InvoiceSettlementAllocation
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "amount_invoice" in self.fields:
            self.fields["amount_invoice"].required = False
            self.fields["amount_invoice"].help_text = (
                "Leave blank to use the invoice total (invoice lines only)."
            )
        if "amount_settlement" in self.fields:
            self.fields["amount_settlement"].required = False
            self.fields["amount_settlement"].help_text = (
                "Leave blank to convert the invoice total into the bank line currency "
                "using stored exchange rates, or leave blank on exactly one fee line "
                "to absorb the remainder."
            )
        if "invoice" in self.fields:
            self.apply_inline_parent_fk_tweaks()

    def apply_inline_parent_fk_tweaks(self) -> None:
        """Invoice FK may be injected by ``InlineModelAdmin.add_fields`` after ``__init__``."""
        if "invoice" not in self.fields:
            return
        self.fields["invoice"].required = False
        self.fields["invoice"].help_text = (
            "Leave empty for a fee / FX / rounding line (bank currency only)."
        )

    def clean(self):
        data = super().clean()
        transaction = data.get("transaction")
        if transaction is None:
            return data

        invoice = data.get("invoice")
        if invoice is None and getattr(self.instance, "invoice_id", None):
            invoice = self.instance.invoice

        if invoice is None:
            data["amount_invoice"] = None
            return data

        amount_invoice = data.get("amount_invoice")
        if amount_invoice is None:
            amount_invoice = (
                invoice.total_amount
                if invoice.total_amount is not None
                else Decimal("0")
            )
            data["amount_invoice"] = amount_invoice

        amount_settlement = data.get("amount_settlement")
        if amount_settlement is None:
            if invoice.currency_id == transaction.currency_id:
                data["amount_settlement"] = amount_invoice
            else:
                converted = amount_in_transaction_currency(
                    amount=amount_invoice,
                    from_currency_id=invoice.currency_id,
                    to_currency_id=transaction.currency_id,
                    as_of=transaction.date,
                )
                if converted is not None:
                    data["amount_settlement"] = converted
                elif invoice.converted_amount is not None:
                    data["amount_settlement"] = invoice.converted_amount
                else:
                    raise forms.ValidationError(
                        {
                            "amount_settlement": (
                                "No exchange rate from the invoice currency to the "
                                "transaction currency — add a rate in Money → Exchange "
                                "rates, set the invoice converted amount, or enter the "
                                "settlement amount manually."
                            )
                        }
                    )

        return data
