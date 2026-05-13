from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class FiscalPeriod(BaseModel):
    """A monthly period for accounting close & validation."""

    STATUS_OPEN = "open"
    STATUS_CLOSED = "closed"
    STATUS_LOCKED = "locked"
    STATUS_CHOICES = (
        (STATUS_OPEN, "Open"),
        (STATUS_CLOSED, "Closed"),
        (STATUS_LOCKED, "Locked"),
    )

    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_OPEN
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_periods",
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "accounting_fiscal_period"
        ordering = ["-year", "-month"]
        unique_together = ("year", "month")
        verbose_name = "Fiscal period"
        verbose_name_plural = "Fiscal periods"

    def __str__(self) -> str:
        return f"{self.year}-{self.month:02d} ({self.get_status_display()})"

    @property
    def label(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    @property
    def is_open(self) -> bool:
        return self.status == self.STATUS_OPEN

    @property
    def is_locked(self) -> bool:
        return self.status == self.STATUS_LOCKED


class PeriodAccountBalance(BaseModel):
    """Per-`Account` opening/closing balance reconciliation for a `FiscalPeriod`.

    `starting_balance` defaults to the previous period's `ending_balance`.
    `ending_balance` is what the bank/cash actually reports at the end of the
    period (entered manually from the bank statement). The computed fields are
    refreshed by `accounting.services.balance.recompute_period_balances`.
    """

    period = models.ForeignKey(
        FiscalPeriod, on_delete=models.CASCADE, related_name="balances"
    )
    account = models.ForeignKey(
        "money.Account", on_delete=models.CASCADE, related_name="period_balances"
    )
    starting_balance = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0")
    )
    ending_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Reported balance at end of period (from bank/cash statement).",
    )
    computed_flow = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Auto: signed sum of transactions in this period for this account.",
    )
    computed_ending = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Auto: starting_balance + computed_flow.",
    )
    discrepancy = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Auto: ending_balance - computed_ending. Zero means balanced.",
    )
    is_balanced = models.BooleanField(default=False)
    last_reconciled_at = models.DateTimeField(null=True, blank=True)
    opening_confirmed_at = models.DateTimeField(null=True, blank=True)
    opening_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_period_openings",
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "accounting_period_account_balance"
        ordering = ["period", "account"]
        unique_together = ("period", "account")
        verbose_name = "Period account balance"
        verbose_name_plural = "Period account balances"

    def __str__(self) -> str:
        flag = "OK" if self.is_balanced else "MISMATCH"
        return f"{self.period.label} {self.account.name}: {flag}"

    @property
    def is_opening_confirmed(self) -> bool:
        return self.opening_confirmed_at is not None


class Daybook(FiscalPeriod):
    """Proxy of `FiscalPeriod` exposing the monthly multi-account daybook view in admin."""

    class Meta:
        proxy = True
        verbose_name = "Daybook"
        verbose_name_plural = "Daybooks"


class AccountingExport(BaseModel):
    """Audit log of generated XLS packages."""

    KIND_DAYBOOK = "daybook"
    KIND_INCOME_STATEMENT = "income_statement"
    KIND_BALANCE = "balance"
    KIND_FULL_PACKAGE = "full_package"
    KIND_FULL_YEAR_PACKAGE = "full_year_package"
    KIND_CHOICES = (
        (KIND_DAYBOOK, "Daybook"),
        (KIND_INCOME_STATEMENT, "Income statement"),
        (KIND_BALANCE, "Balance"),
        (KIND_FULL_PACKAGE, "Full monthly package"),
        (KIND_FULL_YEAR_PACKAGE, "Full yearly package"),
    )

    period = models.ForeignKey(
        FiscalPeriod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exports",
    )
    kind = models.CharField(max_length=32, choices=KIND_CHOICES)
    file_path = models.CharField(max_length=500, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accounting_exports",
    )
    parameters_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "accounting_export"
        ordering = ["-generated_at"]
        verbose_name = "Accounting export"
        verbose_name_plural = "Accounting exports"

    def __str__(self) -> str:
        period_label = self.period.label if self.period else "n/a"
        return f"{self.get_kind_display()} for {period_label}"
