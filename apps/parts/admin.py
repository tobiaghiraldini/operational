from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.parts.models import ApiKey, Credential, Part


@admin.register(Part)
class PartAdmin(ModelAdmin):
    list_display = ("name", "part_type", "content_type", "object_id", "expires_at")
    list_filter = ("part_type",)


@admin.register(ApiKey)
class ApiKeyAdmin(ModelAdmin):
    list_display = ("name", "environment", "next_rotation_due")
    list_filter = ("environment",)


@admin.register(Credential)
class CredentialAdmin(ModelAdmin):
    list_display = ("name", "credential_kind", "next_rotation_due")
    list_filter = ("credential_kind",)
