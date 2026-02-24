"""
Create the first (public) tenant for local development.
Run from project root: python apps/customers/scripts/create_first_tenant_local.py
"""
import os
import sys
import django
from apps.customers.models import Client, Domain

# Add project root to path and set up Django before any Django imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "operational.settings")


django.setup()


tenant = Client(
    schema_name="public", name="Tobia", paid_until="2099-12-31", on_trial=False
)
tenant.save()

# Add one or more domains for the tenant
domain = Domain()
domain.domain = "localhost"  # don't add your port or www here! on a local server you'll want to use localhost here
domain.tenant = tenant
domain.is_primary = True
domain.save()
