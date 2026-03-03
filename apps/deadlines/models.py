from django.db import models


class Deadline(models.Model):
    """Deadline: due date for payments, milestones, expiring parts, etc. Tenant-scoped."""

    class DeadlineType(models.TextChoices):
        PAYMENT = "payment", "Payment"
        CONTRACT = "contract", "Contract"
        RENEWAL = "renewal", "Renewal"
        COMPLIANCE = "compliance", "Compliance"
        EXPIRING_TOKEN = "expiring_token", "Expiring token/account"
        PRODUCT_MILESTONE = "product_milestone", "Product milestone"
        PLAN_MILESTONE = "plan_milestone", "Plan milestone"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DONE = "done", "Done"
        OVERDUE = "overdue", "Overdue"

    title = models.CharField(max_length=255)
    deadline_type = models.CharField(
        max_length=30,
        choices=DeadlineType.choices,
        default=DeadlineType.OTHER,
    )
    due_date = models.DateField()
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "deadlines_deadline"
        ordering = ["due_date", "title"]
        verbose_name = "Deadline"
        verbose_name_plural = "Deadlines"

    def __str__(self):
        return f"{self.title} ({self.due_date})"
