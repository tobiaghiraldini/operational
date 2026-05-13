"""Inline formset on Transaction: one blank fee line absorbs bank-line remainder."""
from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.money.forms.settlement_allocation_inline_formset import (
    SettlementAllocationInlineFormSet,
)


class TransactionSettlementAllocationFormSet(SettlementAllocationInlineFormSet):
    """After invoice lines get FX defaults, optionally fill a single fee row gap."""

    def get_form_kwargs(self, index):
        """Extra lines default ``transaction`` to the parent; that makes ``has_changed()`` false.

        Django would then skip field validation entirely, so a fee row (no invoice,
        blank settlement) never reaches ``clean()`` — fix by always validating rows.
        """
        kwargs = super().get_form_kwargs(index)
        kwargs["empty_permitted"] = False
        return kwargs

    def clean(self):
        super().clean()
        tx = self.instance
        if tx is None or tx.pk is None:
            return

        active_forms = [
            f
            for f in self.forms
            if hasattr(f, "cleaned_data")
            and f.cleaned_data
            and not f.cleaned_data.get("DELETE", False)
        ]

        def settlement_amount(f) -> Decimal:
            v = f.cleaned_data.get("amount_settlement")
            return v if v is not None else Decimal("0")

        total = sum(settlement_amount(f) for f in active_forms)
        blank_fee = [
            f
            for f in active_forms
            if f.cleaned_data.get("invoice") is None
            and f.cleaned_data.get("amount_settlement") is None
        ]

        tx_amount = tx.amount or Decimal("0")
        remainder = tx_amount - total

        if len(blank_fee) == 1:
            if remainder < -Decimal("0.02"):
                raise ValidationError(
                    "Allocated settlement amounts exceed the transaction amount."
                )
            blank_fee[0].cleaned_data["amount_settlement"] = max(remainder, Decimal("0"))
            blank_fee[0].cleaned_data["amount_invoice"] = None
        elif len(blank_fee) > 1:
            raise ValidationError(
                "Only one fee line (no invoice) can have a blank settlement amount "
                "to absorb the remainder."
            )

        total = sum(settlement_amount(f) for f in active_forms)
        remainder = tx_amount - total
        if abs(remainder) > Decimal("0.02"):
            raise ValidationError(
                f"Settlement allocations must sum to the transaction amount ({tx_amount}); "
                f"current total is {total}. Add or adjust a fee line (no invoice), or correct "
                "invoice amounts."
            )
