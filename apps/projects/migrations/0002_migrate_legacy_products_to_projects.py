"""Copy legacy products_product rows (project semantics) into projects_project."""

from django.db import migrations


def migrate_products_to_projects(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    Project = apps.get_model("projects", "Project")
    ContentType = apps.get_model("contenttypes", "ContentType")
    Part = apps.get_model("parts", "Part")

    if not Product.objects.exists():
        return

    product_ct = ContentType.objects.filter(
        app_label="products", model="product"
    ).first()
    project_ct = ContentType.objects.filter(
        app_label="projects", model="project"
    ).first()
    if not product_ct or not project_ct:
        return

    id_map = {}
    for old in Product.objects.all():
        status = getattr(old, "status", "idea")
        project = Project.objects.create(
            name=old.name,
            slug=old.slug,
            description=old.description,
            status=status,
            created_at=old.created_at,
            updated_at=old.updated_at,
        )
        id_map[old.pk] = project.pk

    for part in Part.objects.filter(content_type_id=product_ct.pk):
        new_id = id_map.get(part.object_id)
        if new_id:
            part.content_type_id = project_ct.pk
            part.object_id = new_id
            part.save(update_fields=["content_type_id", "object_id"])

    Product.objects.all().delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("parts", "0001_initial"),
        ("products", "0001_initial"),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(migrate_products_to_projects, noop),
    ]
