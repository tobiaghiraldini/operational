# Data migration: copy public-schema TenantCompanyProfile into tenant Organization rows.

from django.db import connection, migrations
from django_tenants.utils import get_public_schema_name


def copy_profile_into_this_tenant_schema(apps, schema_editor):
    public = get_public_schema_name()
    schema_name = connection.schema_name
    if not schema_name or schema_name == public:
        return

    TenantCompanyProfile = apps.get_model("tenants", "TenantCompanyProfile")
    Organization = apps.get_model("organizations", "Organization")
    Tenant = apps.get_model("tenants", "Tenant")

    connection.set_schema_to_public()
    try:
        tenant = Tenant.objects.filter(schema_name=schema_name).first()
        if tenant is None:
            return
        tenant_pk = tenant.pk
        tenant_name = tenant.name

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = %s
                      AND table_name = 'tenants_tenantcompanyprofile'
                )
                """,
                [public],
            )
            profile_table_exists = cursor.fetchone()[0]

        if profile_table_exists:
            profile = TenantCompanyProfile.objects.filter(tenant_id=tenant_pk).first()
        else:
            profile = None
    finally:
        connection.set_schema(schema_name, include_public=False)

    if profile is None:
        return

    Organization.objects.update_or_create(
        tenant_id=tenant_pk,
        defaults={
            "name": profile.trading_name or profile.legal_name or tenant_name,
            "description": "",
            "legal_name": profile.legal_name,
            "trading_name": profile.trading_name,
            "vat_id": profile.vat_id,
            "tax_id": profile.tax_code,
            "address_line1": profile.address_line1,
            "address_line2": profile.address_line2,
            "legal_address": "",
            "city": profile.city,
            "postal_code": profile.postal_code,
            "country_code": profile.country_code or "IT",
            "trading_aliases": list(profile.trading_aliases or []),
            "email": profile.email,
            "phone": profile.phone,
            "website": profile.website,
        },
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0002_alter_organization_options_and_more"),
        ("tenants", "0003_tenant_company_profile"),
    ]

    operations = [
        migrations.RunPython(copy_profile_into_this_tenant_schema, noop_reverse),
    ]
