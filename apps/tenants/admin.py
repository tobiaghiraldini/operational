from django.contrib import admin
from django_tenants.admin import TenantAdminMixin
from unfold.admin import ModelAdmin

from apps.core.admin_mixins import PublicSchemaOnlyAdminMixin
from apps.tenants.models import Domain, Tenant


@admin.register(Tenant)
class TenantAdmin(PublicSchemaOnlyAdminMixin, TenantAdminMixin, ModelAdmin):
    list_display = ("name", "schema_name", "owner", "status", "paid_until")
    search_fields = ("name", "slug", "schema_name")
    list_filter = ("status", "on_trial")


@admin.register(Domain)
class DomainAdmin(PublicSchemaOnlyAdminMixin, TenantAdminMixin, ModelAdmin):
    list_display = ("domain", "tenant", "is_primary")
    search_fields = ("domain", "tenant__name")
