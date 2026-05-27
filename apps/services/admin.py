from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.services.models import ExternalService, Integration, ServiceCredential


class ServiceCredentialInline(TabularInline):
    model = ServiceCredential
    extra = 0


class IntegrationInline(TabularInline):
    model = Integration
    extra = 0


@admin.register(ExternalService)
class ExternalServiceAdmin(ModelAdmin):
    list_display = ("name", "slug", "service_type", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ServiceCredentialInline, IntegrationInline]


@admin.register(Integration)
class IntegrationAdmin(ModelAdmin):
    list_display = ("name", "external_service", "project", "status")
    list_filter = ("status", "integration_type")


@admin.register(ServiceCredential)
class ServiceCredentialAdmin(ModelAdmin):
    list_display = (
        "name",
        "external_service",
        "project",
        "next_rotation_due",
        "created_at",
    )
    list_filter = ("external_service",)
    raw_id_fields = ("external_service", "project")
