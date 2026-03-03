from django.db import models


class Milestone(models.Model):
    """Milestone: goal with dates and details; belongs to a plan. Tenant-scoped."""

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"

    plan = models.ForeignKey(
        "plans.Plan",
        on_delete=models.CASCADE,
        related_name="milestones",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    target_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "milestones_milestone"
        ordering = ["plan", "order", "target_date"]
        verbose_name = "Milestone"
        verbose_name_plural = "Milestones"

    def __str__(self):
        return f"{self.name} ({self.plan.name})"
