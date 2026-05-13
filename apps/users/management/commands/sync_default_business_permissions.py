"""Re-apply DefaultBusinessPermissionsPolicy grants for existing tenant staff.

Run after migrations add new models under whitelisted app labels (e.g. money)
so UserTenantPermissions rows pick up new auth.Permission rows.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django_tenants.utils import tenant_context
from tenant_users.permissions.models import UserTenantPermissions

from apps.tenants.models import Tenant
from apps.users.services.default_business_permissions_policy import (
    DefaultBusinessPermissionsPolicy,
)


class Command(BaseCommand):
    help = (
        "For each tenant schema, re-run default business permission grants for "
        "staff (non-superuser) UserTenantPermissions rows. Idempotent."
    )

    def handle(self, *args, **options):
        policy = DefaultBusinessPermissionsPolicy()
        total = 0
        for tenant in Tenant.objects.exclude(schema_name="public").order_by(
            "schema_name"
        ):
            with tenant_context(tenant):
                qs = UserTenantPermissions.objects.filter(
                    is_staff=True, is_superuser=False
                )
                n = 0
                for row in qs.iterator(chunk_size=100):
                    policy.grant(
                        tenant_perms=row,
                        is_staff=True,
                        is_superuser=False,
                    )
                    n += 1
                if n:
                    self.stdout.write(
                        f"{tenant.schema_name}: refreshed grants for {n} staff permission row(s)"
                    )
                total += n
        self.stdout.write(
            self.style.SUCCESS(f"Done. Processed {total} staff permission row(s).")
        )
