from django.db import models
from apps.core.models import BaseModel


class Organization(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    legal_name = models.CharField(max_length=255, blank=True)
    vat_id = models.CharField(max_length=64, blank=True)
    tax_id = models.CharField(max_length=64, blank=True)
    legal_address = models.TextField(blank=True)
    city = models.CharField(max_length=128, blank=True)
    postal_code = models.CharField(max_length=32, blank=True)
    country_code = models.CharField(max_length=2, default="IT")
    website = models.URLField(blank=True)
    logo_url = models.URLField(blank=True)
    tenant = models.OneToOneField(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="organization",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.legal_name or self.name
