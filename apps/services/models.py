from django.db import models


class ExternalService(models.Model):
    """Registry of external services (e.g. Stripe, SendGrid). Tenant-scoped definition of 'we use this service'."""

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


class ServiceCredential(models.Model):
    """Stored credential for an external service (tenant or product scope). Tenant-scoped."""

    external_service = models.ForeignKey(
        ExternalService,
        on_delete=models.CASCADE,
        related_name="credentials",
    )
    name = models.CharField(max_length=255)
    # Scope: tenant-level vs product-level (product_id optional).
    # Encrypted value in real impl; placeholder here.
    value_encrypted = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "services_service_credential"
        ordering = ["external_service", "name"]
        verbose_name = "Service credential"
        verbose_name_plural = "Service credentials"

    def __str__(self):
        return f"{self.external_service.name}: {self.name}"
