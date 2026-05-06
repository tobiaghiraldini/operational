from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.core.admin_mixins import TenantSchemaOnlyAdminMixin
from apps.customers.models import Customer


@admin.register(Customer)
class CustomerAdmin(TenantSchemaOnlyAdminMixin, ModelAdmin):
    list_display = ("name", "vat_id", "email", "is_active")
    search_fields = ("name", "vat_id", "email")
    list_filter = ("is_active", "country_code")