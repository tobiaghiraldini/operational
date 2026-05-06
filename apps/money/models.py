from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Currency(BaseModel):
    """ISO 4217 currency. Tenant-scoped (each tenant maintains its own active list)."""

    code = models.CharField(max_length=3, unique=True, help_text="ISO 4217 code, e.g. EUR")
    name = models.CharField(max_length=64)
    symbol = models.CharField(max_length=8, blank=True)
    decimal_places = models.PositiveSmallIntegerField(default=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "money_currency"
        ordering = ["code"]
        verbose_name = "Currency"
        verbose_name_plural = "Currencies"

    def __str__(self) -> str:
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.code.upper().strip()
        super().save(*args, **kwargs)


class ExchangeRate(BaseModel):
    """A `from_currency` -> `to_currency` rate effective from `valid_from`."""

    SOURCE_MANUAL = "manual"
    SOURCE_ECB = "ecb"
    SOURCE_API = "api"
    SOURCE_CHOICES = (
        (SOURCE_MANUAL, "Manual"),
        (SOURCE_ECB, "ECB"),
        (SOURCE_API, "External API"),
    )

    from_currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE, related_name="rates_from"
    )
    to_currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE, related_name="rates_to"
    )
    rate = models.DecimalField(max_digits=18, decimal_places=8)
    valid_from = models.DateField()
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default=SOURCE_MANUAL)

    class Meta:
        db_table = "money_exchange_rate"
        ordering = ["-valid_from"]
        unique_together = ("from_currency", "to_currency", "valid_from")
        indexes = [
            models.Index(fields=["from_currency", "to_currency", "-valid_from"]),
        ]

    def __str__(self) -> str:
        return f"{self.from_currency.code}->{self.to_currency.code} @ {self.rate} ({self.valid_from})"


class Account(BaseModel):
    """A bank account or cash register held by the tenant."""

    KIND_BANK = "bank"
    KIND_CASH = "cash"
    KIND_OTHER = "other"
    KIND_CHOICES = (
        (KIND_BANK, "Bank"),
        (KIND_CASH, "Cash"),
        (KIND_OTHER, "Other"),
    )

    name = models.CharField(max_length=128)
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, default=KIND_BANK)
    iban = models.CharField(max_length=34, blank=True)
    bank_name = models.CharField(max_length=128, blank=True)
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="accounts"
    )
    opening_balance = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0")
    )
    opening_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "money_account"
        ordering = ["kind", "name"]
        verbose_name = "Account"
        verbose_name_plural = "Accounts"

    def __str__(self) -> str:
        return f"{self.name} ({self.get_kind_display()}, {self.currency.code})"


class TransactionCategory(BaseModel):
    """Income/expense/transfer category. Tenant-scoped, supports one level of grouping."""

    KIND_INCOME = "income"
    KIND_EXPENSE = "expense"
    KIND_TRANSFER = "transfer"
    KIND_CHOICES = (
        (KIND_INCOME, "Income"),
        (KIND_EXPENSE, "Expense"),
        (KIND_TRANSFER, "Transfer"),
    )

    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=128, unique=True)
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, default=KIND_EXPENSE)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "money_transaction_category"
        ordering = ["kind", "name"]
        verbose_name = "Transaction category"
        verbose_name_plural = "Transaction categories"

    def __str__(self) -> str:
        return f"{self.name} ({self.get_kind_display()})"


class BankStatement(BaseModel):
    """Imported bank statement document covering a date range."""

    PARSE_PENDING = "pending"
    PARSE_PARSED = "parsed"
    PARSE_ERROR = "error"
    PARSE_CHOICES = (
        (PARSE_PENDING, "Pending"),
        (PARSE_PARSED, "Parsed"),
        (PARSE_ERROR, "Error"),
    )

    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="statements"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=14, decimal_places=2)
    document = models.ForeignKey(
        "documents.DocumentFile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bank_statements",
    )
    parse_status = models.CharField(
        max_length=16, choices=PARSE_CHOICES, default=PARSE_PENDING
    )
    raw_text = models.TextField(blank=True)
    parse_error = models.TextField(blank=True)

    class Meta:
        db_table = "money_bank_statement"
        ordering = ["-period_end"]
        indexes = [models.Index(fields=["account", "-period_end"])]
        verbose_name = "Bank statement"
        verbose_name_plural = "Bank statements"

    def __str__(self) -> str:
        return f"{self.account.name} {self.period_start}..{self.period_end}"


class BankStatementLine(BaseModel):
    """A single line parsed from a bank statement, optionally matched to a Transaction."""

    DIRECTION_IN = "in"
    DIRECTION_OUT = "out"
    DIRECTION_CHOICES = (
        (DIRECTION_IN, "In"),
        (DIRECTION_OUT, "Out"),
    )

    statement = models.ForeignKey(
        BankStatement, on_delete=models.CASCADE, related_name="lines"
    )
    date = models.DateField()
    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES)
    amount = models.DecimalField(
        max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    description = models.TextField(blank=True)
    bank_reference = models.CharField(max_length=100, blank=True)
    matched_transaction = models.ForeignKey(
        "money.Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matched_statement_lines",
    )
    is_matched = models.BooleanField(default=False)

    class Meta:
        db_table = "money_bank_statement_line"
        ordering = ["date", "id"]
        indexes = [models.Index(fields=["statement", "date"])]

    def __str__(self) -> str:
        return f"{self.date} {self.direction} {self.amount} {self.description[:40]}"


class Transaction(BaseModel):
    """A single cash/bank money movement -- the canonical Daybook (Prima Nota) line."""

    DIRECTION_IN = "in"
    DIRECTION_OUT = "out"
    DIRECTION_CHOICES = (
        (DIRECTION_IN, "In"),
        (DIRECTION_OUT, "Out"),
    )

    date = models.DateField()
    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES)
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Always positive; sign comes from `direction`.",
    )
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="transactions"
    )
    base_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount converted to the tenant's base currency (snapshot).",
    )
    exchange_rate = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="Snapshot of the rate used to compute base_amount.",
    )

    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="transactions"
    )
    category = models.ForeignKey(
        TransactionCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )

    counterparty = models.CharField(
        max_length=255,
        blank=True,
        help_text="Cached counterparty name for fast display/search.",
    )
    description = models.TextField(blank=True)
    reference = models.CharField(
        max_length=100, blank=True, help_text="Bank reference, document #, etc."
    )

    invoice = models.ForeignKey(
        "invoices.Invoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    vendor = models.ForeignKey(
        "vendors.Vendor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    document = models.ForeignKey(
        "documents.DocumentFile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    bank_statement_line = models.OneToOneField(
        BankStatementLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transaction",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_transactions",
    )

    class Meta:
        db_table = "money_transaction"
        ordering = ["-date", "-id"]
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        indexes = [
            models.Index(fields=["account", "date"]),
            models.Index(fields=["date", "direction"]),
            models.Index(fields=["invoice"]),
        ]

    def __str__(self) -> str:
        sign = "+" if self.direction == self.DIRECTION_IN else "-"
        return f"{self.date} {sign}{self.amount} {self.currency.code} {self.counterparty or self.description[:40]}"

    @property
    def signed_amount(self) -> Decimal:
        """Positive for IN, negative for OUT."""
        return self.amount if self.direction == self.DIRECTION_IN else -self.amount

    @property
    def signed_base_amount(self) -> Decimal | None:
        if self.base_amount is None:
            return None
        return (
            self.base_amount
            if self.direction == self.DIRECTION_IN
            else -self.base_amount
        )
