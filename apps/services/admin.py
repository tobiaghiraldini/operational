from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import ExternalService, ServiceCredential


class ServiceCredentialInline(admin.TabularInline):
    model = ServiceCredential
    extra = 0


@admin.register(ExternalService)
class ExternalServiceAdmin(ModelAdmin):
    list_display = ("name", "slug", "service_type", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ServiceCredentialInline]


@admin.register(ServiceCredential)
class ServiceCredentialAdmin(ModelAdmin):
    list_display = ("name", "external_service", "created_at")
    list_filter = ("external_service",)
    raw_id_fields = ("external_service",)
