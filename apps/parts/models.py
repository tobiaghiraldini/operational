from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class PartParentMixin(models.Model):
    """Shared generic parent: Project or System."""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        abstract = True


class Part(PartParentMixin, models.Model):
    """Part: token, account, license, or other traceable asset."""

    class PartType(models.TextChoices):
        TOKEN = "token", "Token"
        ACCOUNT = "account", "Account"
        LICENSE = "license", "License"
        OTHER = "other", "Other"

    name = models.CharField(max_length=255)
    part_type = models.CharField(
        max_length=20,
        choices=PartType.choices,
        default=PartType.OTHER,
    )
    description = models.TextField(blank=True)
    value_masked = models.CharField(max_length=100, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "parts_part"
        ordering = ["name"]
        verbose_name = "Part"
        verbose_name_plural = "Parts"

    def __str__(self):
        return f"{self.name} ({self.get_part_type_display()})"


class ApiKey(PartParentMixin, models.Model):
    """First-class API key with rotation tracking."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    value_masked = models.CharField(max_length=100, blank=True)
    scope = models.CharField(max_length=255, blank=True)
    environment = models.CharField(max_length=50, blank=True)
    last_rotated_at = models.DateTimeField(null=True, blank=True)
    next_rotation_due = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "parts_api_key"
        ordering = ["name"]
        verbose_name = "API key"
        verbose_name_plural = "API keys"

    def __str__(self):
        return self.name


class Credential(PartParentMixin, models.Model):
    """First-class credential (secrets, OAuth, certificates)."""

    class CredentialKind(models.TextChoices):
        API_SECRET = "api_secret", "API secret"
        OAUTH = "oauth", "OAuth"
        PASSWORD = "password", "Password"
        CERT = "cert", "Certificate"
        OTHER = "other", "Other"

    name = models.CharField(max_length=255)
    credential_kind = models.CharField(
        max_length=20,
        choices=CredentialKind.choices,
        default=CredentialKind.OTHER,
    )
    description = models.TextField(blank=True)
    value_masked = models.CharField(max_length=100, blank=True)
    scope = models.CharField(max_length=255, blank=True)
    environment = models.CharField(max_length=50, blank=True)
    last_rotated_at = models.DateTimeField(null=True, blank=True)
    next_rotation_due = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "parts_credential"
        ordering = ["name"]
        verbose_name = "Credential"
        verbose_name_plural = "Credentials"

    def __str__(self):
        return self.name
