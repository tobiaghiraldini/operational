"""Tenant membership service for tenant-user relationships."""
from django_tenants.utils import tenant_context

from apps.users.services.default_business_permissions_policy import (
    DefaultBusinessPermissionsPolicy,
)


def ensure_tenant_membership(*, user, tenant, is_staff: bool, is_superuser: bool) -> None:
    """Ensure user membership + permission facade row exist for a tenant.

    - If the user is not linked to the tenant, uses `tenant.add_user(...)`.
    - If already linked (e.g. from raw M2M edits), repairs/updates the tenant
      permission row.
    - Applies default business-model permissions through policy.
    """
    from tenant_users.permissions.models import UserTenantPermissions

    if not user.tenants.filter(pk=tenant.pk).exists():
        tenant.add_user(user, is_staff=is_staff, is_superuser=is_superuser)
        return

    with tenant_context(tenant):
        tenant_perms, _ = UserTenantPermissions.objects.get_or_create(profile=user)
        tenant_perms.is_staff = is_staff
        tenant_perms.is_superuser = is_superuser
        tenant_perms.save(update_fields=["is_staff", "is_superuser", "modified_at"])
        DefaultBusinessPermissionsPolicy().grant(
            tenant_perms=tenant_perms,
            is_staff=is_staff,
            is_superuser=is_superuser,
        )
