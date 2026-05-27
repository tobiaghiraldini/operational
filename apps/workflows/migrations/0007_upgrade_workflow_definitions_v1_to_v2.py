# Generated manually for React Flow schema upgrade

from django.db import migrations


def forwards(apps, schema_editor):
    from apps.workflows.services.upgrade_definition_v1_to_v2 import upgrade_v1_document_to_v2

    Workflow = apps.get_model("workflows", "Workflow")
    for wf in Workflow.objects.iterator():
        d = wf.definition
        if not isinstance(d, dict):
            continue
        if d.get("schemaVersion") == 1:
            wf.definition = upgrade_v1_document_to_v2(d)
            wf.save(update_fields=["definition"])


def backwards(apps, schema_editor):
    """No-op: cannot reliably downgrade v2 → v1."""


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0006_workflownodelink_and_v2"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
