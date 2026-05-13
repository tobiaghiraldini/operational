from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.organizations.models import Organization


@admin.register(Organization)
class OrganizationAdmin(ModelAdmin):
    list_display = ("name", "legal_name", "trading_name", "tenant", "vat_id", "country_code")
    search_fields = (
        "name",
        "legal_name",
        "trading_name",
        "vat_id",
        "tax_id",
        "tenant__name",
        "tenant__schema_name",
    )
    raw_id_fields = ("tenant",)
    fieldsets = (
        (None, {"fields": ("tenant", "name", "description")}),
        (
            "Legal / fiscal",
            {
                "fields": (
                    "legal_name",
                    "trading_name",
                    "vat_id",
                    "tax_id",
                    "trading_aliases",
                )
            },
        ),
        (
            "Address",
            {
                "fields": (
                    "address_line1",
                    "address_line2",
                    "legal_address",
                    "city",
                    "postal_code",
                    "country_code",
                )
            },
        ),
        ("Contact & branding", {"fields": ("email", "phone", "website", "logo_url")}),
    )
