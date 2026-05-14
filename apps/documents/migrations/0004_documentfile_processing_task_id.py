from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0003_documentfolder_path_help_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentfile",
            name="processing_task_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Last Celery task id for invoice extraction (django_celery_results).",
                max_length=255,
            ),
        ),
    ]
