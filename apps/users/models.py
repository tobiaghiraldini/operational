from django.db import models
from tenant_users.tenants.models import UserProfile


class TenantUser(UserProfile):
    display_name = models.CharField(max_length=255, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    locale = models.CharField(max_length=16, default="en")
    phone = models.CharField(max_length=32, blank=True)
    avatar = models.URLField(blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    invited_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invited_users",
    )
    last_tenant_schema = models.CharField(max_length=63, blank=True)

    class Meta:
        verbose_name = "Tenant user"
        verbose_name_plural = "Tenant users"

    def __str__(self):
        return self.email
