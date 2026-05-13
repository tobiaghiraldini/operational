"""Human-readable doc # for exports when a transaction settles one or more invoices."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.money.models import Transaction


def transaction_invoice_document_label(tx: "Transaction") -> str:
    if getattr(tx, "reference", None):
        return tx.reference
    cache = getattr(tx, "_prefetched_objects_cache", None)
    allocs = cache.get("invoice_allocations") if cache else None
    if allocs is not None:
        nums = []
        for a in sorted(allocs, key=lambda x: x.pk):
            inv = getattr(a, "invoice", None)
            if inv and inv.invoice_number:
                nums.append(inv.invoice_number)
    else:
        nums = list(
            tx.invoice_allocations.select_related("invoice")
            .order_by("id")
            .values_list("invoice__invoice_number", flat=True)
        )
        nums = [n for n in nums if n]
    if not nums:
        return ""
    if len(nums) == 1:
        return nums[0]
    return f"{nums[0]} +{len(nums) - 1}"
