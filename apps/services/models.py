from django.db import models


class ExternalService(models.Model):
    """Registry of external services (e.g. Stripe, SendGrid)."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    service_type = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "services_external_service"
        ordering = ["name"]
        verbose_name = "External service"
        verbose_name_plural = "External services"

    def __str__(self):
        return self.name


class Integration(models.Model):
    """Tenant usage of an external service, optionally scoped to a project."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        PENDING = "pending", "Pending"

    external_service = models.ForeignKey(
        ExternalService,
        on_delete=models.CASCADE,
        related_name="integrations",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="integrations",
    )
    name = models.CharField(max_length=255, blank=True)
    integration_type = models.CharField(max_length=50, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "services_integration"
        ordering = ["external_service", "name"]
        verbose_name = "Integration"
        verbose_name_plural = "Integrations"

    def __str__(self):
        label = self.name or self.external_service.name
        if self.project_id:
            return f"{label} ({self.project})"
        return label


class ServiceCredential(models.Model):
    """Stored credential for an external service."""

    external_service = models.ForeignKey(
        ExternalService,
        on_delete=models.CASCADE,
        related_name="credentials",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="service_credentials",
    )
    name = models.CharField(max_length=255)
    value_encrypted = models.TextField(blank=True)
    last_rotated_at = models.DateTimeField(null=True, blank=True)
    next_rotation_due = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "services_service_credential"
        ordering = ["external_service", "name"]
        verbose_name = "Service credential"
        verbose_name_plural = "Service credentials"

    def __str__(self):
        return f"{self.external_service.name}: {self.name}"
