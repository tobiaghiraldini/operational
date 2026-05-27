from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0003_projectproduct_project_and_more"),
        ("projects", "0002_migrate_legacy_products_to_projects"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="commercial_products",
            field=models.ManyToManyField(
                blank=True,
                related_name="projects",
                through="products.ProjectProduct",
                to="products.product",
            ),
        ),
    ]
