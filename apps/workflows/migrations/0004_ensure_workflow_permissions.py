"""Ensure default auth permissions exist for ``Workflow``.

``0002_alter_workflow_options`` set ``default_permissions`` to ``()`` so Django
never created ``view_workflow`` / ``change_workflow`` / etc. Staff then hit
``PermissionDenied`` on the admin changelist. ``0003`` restored model options
without that flag, but existing tenant schemas may still lack Permission rows.
This migration creates the four default permissions when missing.
"""

from __future__ import annotations

from django.db import migrations


def forwards(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    ct = ContentType.objects.filter(app_label="workflows", model="workflow").first()
    if ct is None:
        return
    for codename, name in (
        ("add_workflow", "Can add workflow"),
        ("change_workflow", "Can change workflow"),
        ("delete_workflow", "Can delete workflow"),
        ("view_workflow", "Can view workflow"),
    ):
        Permission.objects.get_or_create(
            codename=codename,
            content_type=ct,
            defaults={"name": name},
        )


def backwards(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    ct = ContentType.objects.filter(app_label="workflows", model="workflow").first()
    if ct is None:
        return
    Permission.objects.filter(
        content_type=ct,
        codename__in=("add_workflow", "change_workflow", "delete_workflow", "view_workflow"),
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0003_workflow_category"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
