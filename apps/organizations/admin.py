from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.organizations.models import Organization


@admin.register(Organization)
class OrganizationAdmin(ModelAdmin):
    list_display = ("name", "legal_name", "tenant", "vat_id", "country_code")
    search_fields = ("name", "legal_name", "vat_id", "tax_id", "tenant__name")
