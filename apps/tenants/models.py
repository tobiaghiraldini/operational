from django.db import models
from django_tenants.models import DomainMixin
from tenant_users.tenants.models import TenantBase


class Tenant(TenantBase):
    STATUS_ACTIVE = "active"
    STATUS_SUSPENDED = "suspended"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_SUSPENDED, "Suspended"),
        (STATUS_ARCHIVED, "Archived"),
    )

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    billing_email = models.EmailField(blank=True)
    support_email = models.EmailField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    timezone = models.CharField(max_length=64, default="UTC")
    locale = models.CharField(max_length=16, default="en")
    currency = models.CharField(max_length=3, default="EUR")
    on_trial = models.BooleanField(default=False)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    paid_until = models.DateField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    settings_json = models.JSONField(default=dict, blank=True)
    features_json = models.JSONField(default=dict, blank=True)
    data_retention_days = models.PositiveIntegerField(default=365)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Domain(DomainMixin):
    pass
