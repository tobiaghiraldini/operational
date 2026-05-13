"""Shared inline formset: parent FK is added after ``ModelForm.__init__`` — tweak fields then."""
from __future__ import annotations

from django.forms.models import BaseInlineFormSet

from apps.money.forms.invoice_settlement_allocation_admin import (
    InvoiceSettlementAllocationAdminForm,
)


class SettlementAllocationInlineFormSet(BaseInlineFormSet):
    """Runs ``apply_inline_parent_fk_tweaks`` after Django injects the inline parent FK field."""

    def add_fields(self, form, index):
        super().add_fields(form, index)
        if isinstance(form, InvoiceSettlementAllocationAdminForm):
            form.apply_inline_parent_fk_tweaks()
