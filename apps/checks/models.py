from django.db import models


class PlannedCheck(models.Model):
    """Scheduled operational check (security, performance, resources)."""

    class CheckType(models.TextChoices):
        SECURITY_AUDIT = "security_audit", "Security audit"
        PERFORMANCE = "performance", "Performance"
        RESOURCES = "resources", "Resource consumption"

    check_type = models.CharField(
        max_length=30,
        choices=CheckType.choices,
    )
    name = models.CharField(max_length=255)
    schedule = models.CharField(
        max_length=255,
        blank=True,
        help_text="Cron expression or human-readable interval.",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="planned_checks",
    )
    system = models.ForeignKey(
        "systems.System",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="planned_checks",
    )
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    result = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "checks_planned_check"
        ordering = ["next_run_at", "name"]
        verbose_name = "Planned check"
        verbose_name_plural = "Planned checks"

    def __str__(self):
        return self.name
