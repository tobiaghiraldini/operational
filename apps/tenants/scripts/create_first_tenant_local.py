"""
Bootstrap the public tenant for local development.
Run from project root: python apps/tenants/scripts/create_first_tenant_local.py
"""
import os
import sys

import django

# Add project root to path and set up Django before app imports.
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "operational.settings")

django.setup()

from apps.tenants.services.provisioning import bootstrap_public_tenant  # noqa: E402


if __name__ == "__main__":
    result = bootstrap_public_tenant(
        domain_url=os.getenv("PUBLIC_DOMAIN_URL", "localhost"),
        owner_email=os.getenv("PUBLIC_OWNER_EMAIL", "admin@localhost"),
    )
    print(
        f"Public tenant ready: schema={result.tenant_schema} "
        f"domain={result.domain_url} owner={result.owner_email}"
    )
