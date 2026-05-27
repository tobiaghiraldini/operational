from django.db import models

from apps.core.db.tenant_user_foreign_key import TenantUserForeignKey


class DashboardWidget(models.Model):
    """User-chosen widget on the dashboard. Tenant-scoped (user belongs to tenant)."""

    user = TenantUserForeignKey(
        on_delete=models.CASCADE,
        related_name="dashboard_widgets",
    )
    widget_type = models.CharField(max_length=50)  # e.g. tasks, projects, deadlines
    position = models.PositiveIntegerField(default=0)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dashboard_widget"
        ordering = ["user", "position"]
        verbose_name = "Dashboard widget"
        verbose_name_plural = "Dashboard widgets"

    def __str__(self):
        return f"{self.widget_type} for user {self.user_id}"
