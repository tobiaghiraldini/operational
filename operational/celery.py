import os
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "operational.settings")

_BASE_DIR = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv

    load_dotenv(_BASE_DIR / ".env")
except ImportError:
    pass

from tenant_schemas_celery.app import CeleryApp

app = CeleryApp("operational")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
