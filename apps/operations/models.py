from django.db import models


class OperationalSnapshot(models.Model):
    """Point-in-time operational / live status for a project."""

    class OverallStatus(models.TextChoices):
        HEALTHY = "healthy", "Healthy"
        DEGRADED = "degraded", "Degraded"
        DOWN = "down", "Down"
        UNKNOWN = "unknown", "Unknown"

    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        INTEGRATION = "integration", "Integration"
        AGENT = "agent", "Agent"

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="operational_snapshots",
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    overall_status = models.CharField(
        max_length=20,
        choices=OverallStatus.choices,
        default=OverallStatus.UNKNOWN,
    )
    summary = models.TextField(blank=True)
    checks = models.JSONField(default=list, blank=True)
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
    )

    class Meta:
        db_table = "operations_operational_snapshot"
        ordering = ["-recorded_at"]
        verbose_name = "Operational snapshot"
        verbose_name_plural = "Operational snapshots"

    def __str__(self):
        return f"{self.project} @ {self.recorded_at} ({self.overall_status})"
