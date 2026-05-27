from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Deadline(models.Model):
    """Deadline: due date for payments, milestones, expiring or rotatable assets."""

    class DeadlineType(models.TextChoices):
        PAYMENT = "payment", "Payment"
        CONTRACT = "contract", "Contract"
        RENEWAL = "renewal", "Renewal"
        COMPLIANCE = "compliance", "Compliance"
        EXPIRING_TOKEN = "expiring_token", "Expiring token/account"
        ROTATION_DUE = "rotation_due", "Rotation due"
        PRODUCT_MILESTONE = "product_milestone", "Product milestone"
        PLAN_MILESTONE = "plan_milestone", "Plan milestone"
        PROJECT_MILESTONE = "project_milestone", "Project milestone"
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
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="deadlines",
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey("content_type", "object_id")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "deadlines_deadline"
        ordering = ["due_date", "title"]
        verbose_name = "Deadline"
        verbose_name_plural = "Deadlines"

    def __str__(self):
        return f"{self.title} ({self.due_date})"
