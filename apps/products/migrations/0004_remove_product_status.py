from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0002_migrate_legacy_products_to_projects"),
        ("products", "0003_projectproduct_project_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="product",
            name="status",
        ),
    ]
