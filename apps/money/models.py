from django.db import models


class MoneyCategory(models.Model):
    """Category for income/expense. Tenant-scoped."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "money_category"
        ordering = ["name"]
        verbose_name = "Money category"
        verbose_name_plural = "Money categories"

    def __str__(self):
        return self.name


class Transaction(models.Model):
    """Income or expense transaction. Tenant-scoped."""

    class Kind(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"

    amount = models.DecimalField(max_digits=14, decimal_places=2)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    date = models.DateField()
    category = models.ForeignKey(
        MoneyCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    counterparty = models.CharField(max_length=255, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "money_transaction"
        ordering = ["-date", "-created_at"]
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    def __str__(self):
        return f"{self.get_kind_display()} {self.amount} ({self.date})"
