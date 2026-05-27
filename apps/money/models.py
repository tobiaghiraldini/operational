from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.db.tenant_user_foreign_key import TenantUserForeignKey
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
    is_default = models.BooleanField(
        default=False,
        help_text="Default bank/cash account for automated postings (e.g. invoice payments).",
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "money_account"
        ordering = ["kind", "name"]
        verbose_name = "Account"
        verbose_name_plural = "Accounts"

    def __str__(self) -> str:
        return f"{self.name} ({self.get_kind_display()}, {self.currency.code})"

    def save(self, *args, **kwargs):
        if self.is_default:
            Account.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


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
        (DIRECTION_OUT, "Out"),
        (DIRECTION_IN, "In"),
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
    payment_method = models.ForeignKey(
        'vendors.PaymentMethod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Payment method used",
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

    created_by = TenantUserForeignKey(
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_transactions",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    product_license = models.ForeignKey(
        "products.ProductLicense",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    deadline = models.ForeignKey(
        "deadlines.Deadline",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )

    class Meta:
        db_table = "money_transaction"
        ordering = ["-date", "-id"]
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        indexes = [
            models.Index(fields=["account", "date"]),
            models.Index(fields=["date", "direction"]),
        ]

    def __str__(self) -> str:
        sign = "+" if self.direction == self.DIRECTION_IN else "-"
        desc = (self.counterparty or self.description or "").strip()
        if len(desc) > 48:
            desc = desc[:45] + "…"
        bits = [f"{self.date} {sign}{self.amount} {self.currency.code}"]
        account = getattr(self, "account", None)
        if account is not None:
            bits.append(account.name)
        if self.reference:
            bits.append(f"ref {self.reference}")
        if desc:
            bits.append(desc)
        return " · ".join(bits)

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

    def settlement_allocated_total(self) -> Decimal:
        """Sum of `amount_settlement` on linked invoice rows (transaction currency)."""
        from django.db.models import Sum

        agg = self.invoice_allocations.aggregate(t=Sum("amount_settlement"))
        return agg["t"] or Decimal("0")

    def settlement_allocation_gap(self) -> Decimal:
        """Bank line amount minus allocated settlement portions (fees/rounding)."""
        return self.amount - self.settlement_allocated_total()


class Budget(BaseModel):
    """Spend budget for a category, project, or period."""

    class Period(models.TextChoices):
        MONTH = "month", "Month"
        QUARTER = "quarter", "Quarter"
        YEAR = "year", "Year"

    name = models.CharField(max_length=128)
    category = models.ForeignKey(
        TransactionCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="budgets",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="budgets",
    )
    period = models.CharField(
        max_length=20,
        choices=Period.choices,
        default=Period.MONTH,
    )
    period_start = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    alert_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional percentage (0-100) at which to alert.",
    )

    class Meta:
        db_table = "money_budget"
        ordering = ["-period_start", "name"]
        verbose_name = "Budget"
        verbose_name_plural = "Budgets"

    def __str__(self) -> str:
        return f"{self.name} ({self.period_start})"


class InvoiceSettlementAllocation(BaseModel):
    """Links one bank/cash `Transaction` to one `Invoice` with split amounts."""

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="invoice_allocations",
    )
    invoice = models.ForeignKey(
        "invoices.Invoice",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="settlement_allocations",
        help_text="Invoice this slice settles; leave empty for a fee/FX/rounding line.",
    )
    amount_settlement = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Portion of this transaction in the transaction's currency (e.g. EUR bank line).",
    )
    amount_invoice = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Slice in invoice currency when linked to an invoice; empty for fee-only lines.",
    )
    fx_rate = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="Optional rate used between invoice currency and settlement currency.",
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "money_invoice_settlement_allocation"
        verbose_name = "Invoice settlement allocation"
        verbose_name_plural = "Invoice settlement allocations"
        constraints = [
            models.UniqueConstraint(
                fields=("transaction", "invoice"),
                name="uniq_settlement_tx_invoice",
            )
        ]
        indexes = [
            models.Index(fields=["transaction"]),
            models.Index(fields=["invoice"]),
        ]

    def __str__(self) -> str:
        inv_part = str(self.invoice_id) if self.invoice_id else "fee"
        return f"{self.transaction_id} → {inv_part}: {self.amount_settlement}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.invoice_id:
            if self.amount_invoice is None or self.amount_invoice < 0:
                raise ValidationError(
                    {"amount_invoice": "Invoice lines require a non-negative invoice amount."}
                )
        else:
            if self.amount_invoice is not None:
                raise ValidationError(
                    {"amount_invoice": "Fee-only lines must not set an invoice currency amount."}
                )
            if self.amount_settlement is not None and self.amount_settlement < 0:
                raise ValidationError(
                    {"amount_settlement": "Settlement amount cannot be negative."}
                )
