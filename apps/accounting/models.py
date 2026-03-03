from django.db import models
from decimal import Decimal


class JournalEntry(models.Model):
    """Journal entry for accounting. Tenant-scoped."""

    date = models.DateField()
    reference = models.CharField(max_length=100, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounting_journal_entry"
        ordering = ["-date", "-created_at"]
        verbose_name = "Journal entry"
        verbose_name_plural = "Journal entries"

    def __str__(self):
        return f"{self.date} {self.reference or self.pk}"


class JournalEntryLine(models.Model):
    """Single line (debit or credit) of a journal entry."""

    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    account_code = models.CharField(max_length=50)
    label = models.CharField(max_length=255, blank=True)
    debit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
    )
    credit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
    )

    class Meta:
        db_table = "accounting_journal_entry_line"
        verbose_name = "Journal entry line"
        verbose_name_plural = "Journal entry lines"

    def __str__(self):
        return f"{self.account_code} dr={self.debit} cr={self.credit}"
