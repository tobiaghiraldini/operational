from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0003_tenant_company_profile"),
        ("organizations", "0003_copy_tenant_company_profile"),
    ]

    operations = [
        migrations.DeleteModel(name="TenantCompanyProfile"),
    ]
