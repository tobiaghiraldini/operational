from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Part(models.Model):
    """Part: token, account, API key, credential. Belongs to a system or product. Tenant-scoped."""

    class PartType(models.TextChoices):
        TOKEN = "token", "Token"
        ACCOUNT = "account", "Account"
        API_KEY = "api_key", "API key"
        CREDENTIAL = "credential", "Credential"
        LICENSE = "license", "License"
        OTHER = "other", "Other"

    # Generic parent: System or Product (or other entity later)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    name = models.CharField(max_length=255)
    part_type = models.CharField(
        max_length=20,
        choices=PartType.choices,
        default=PartType.OTHER,
    )
    description = models.TextField(blank=True)
    # Sensitive value: store encrypted or hashed; mask in UI.
    value_masked = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "parts_part"
        ordering = ["name"]
        verbose_name = "Part"
        verbose_name_plural = "Parts"

    def __str__(self):
        return f"{self.name} ({self.get_part_type_display()})"
