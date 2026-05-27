from django.db import models

from apps.core.db.tenant_user_foreign_key import TenantUserForeignKey


class System(models.Model):
    """System: reusable logical capability (app, service, platform piece)."""

    class SystemType(models.TextChoices):
        INFRASTRUCTURE = "infrastructure", "Infrastructure"
        MULTI_TENANT = "multi_tenant", "Multi-tenant system"
        AUTHENTICATION = "authentication", "Authentication system"
        PERMISSIONS = "permissions", "Permissions system"
        BACKGROUND_TASKS = "background_tasks", "Background tasks system"
        OBSERVABILITY = "observability", "Observability system"
        API_CLIENT = "api_client", "API client system"
        MCP_SERVER = "mcp_server", "MCP server system"
        API = "api", "API"
        INTEGRATION = "integration", "Integration layer"
        DATA_STORE = "data_store", "Data store"
        MESSAGING = "messaging", "Messaging"
        OTHER = "other", "Other"

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    system_type = models.CharField(
        max_length=30,
        choices=SystemType.choices,
        default=SystemType.OTHER,
    )
    description = models.TextField(blank=True)
    environment = models.CharField(max_length=50, blank=True)
    scope = models.CharField(max_length=255, blank=True)
    owner = TenantUserForeignKey(
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_systems",
    )
    repo_url = models.URLField(blank=True)
    docs_url = models.URLField(blank=True)
    dashboard_url = models.URLField(blank=True)
    depends_on = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="depended_on_by",
    )
    topics = models.ManyToManyField(
        "topics.Topic",
        blank=True,
        related_name="systems",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "systems_system"
        ordering = ["name"]
        verbose_name = "System"
        verbose_name_plural = "Systems"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify

            base = slugify(self.name)[:240] or "system"
            slug = base
            n = 1
            while System.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)
