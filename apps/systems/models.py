from django.db import models


class System(models.Model):
    """System: reusable capability (app, service, infra). Made of parts. Tenant-scoped."""

    class SystemType(models.TextChoices):
        INFRASTRUCTURE = "infrastructure", "Infrastructure"
        MULTI_TENANT = "multi_tenant", "Multi-tenant system"
        AUTHENTICATION = "authentication", "Authentication system"
        PERMISSIONS = "permissions", "Permissions system"
        BACKGROUND_TASKS = "background_tasks", "Background tasks system"
        OBSERVABILITY = "observability", "Observability system"
        API_CLIENT = "api_client", "API client system"
        MCP_SERVER = "mcp_server", "MCP server system"
        OTHER = "other", "Other"

    name = models.CharField(max_length=255)
    system_type = models.CharField(
        max_length=30,
        choices=SystemType.choices,
        default=SystemType.OTHER,
    )
    description = models.TextField(blank=True)
    environment = models.CharField(max_length=50, blank=True)  # prod, staging, etc.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "systems_system"
        ordering = ["name"]
        verbose_name = "System"
        verbose_name_plural = "Systems"

    def __str__(self):
        return self.name
