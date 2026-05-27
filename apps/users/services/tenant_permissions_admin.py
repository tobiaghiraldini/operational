"""Tenant-scoped permission helpers for public admin (edit rows in tenant schema)."""

from __future__ import annotations

from django.contrib.auth.models import Permission
from django_tenants.utils import tenant_context

from apps.users.services.default_business_permissions_policy import (
    DefaultBusinessPermissionsPolicy,
)


def clear_profile_permission_cache(user) -> None:
    from tenant_users.constants import TENANT_CACHE_NAME

    user.__dict__.pop(TENANT_CACHE_NAME, None)


def get_tenant_permissions_row(*, user, tenant):
    """Return UserTenantPermissions for user in tenant schema, or None."""
    from tenant_users.permissions.models import UserTenantPermissions

    with tenant_context(tenant):
        return UserTenantPermissions.objects.filter(profile_id=user.pk).first()


def apply_default_business_permissions(*, user, tenant) -> int:
    """Grant APP_LABELS permissions to staff user in tenant schema."""
    from tenant_users.permissions.models import UserTenantPermissions

    with tenant_context(tenant):
        tenant_perms, _ = UserTenantPermissions.objects.get_or_create(profile=user)
        if not tenant_perms.is_staff or tenant_perms.is_superuser:
            return 0
        count = DefaultBusinessPermissionsPolicy().grant(
            tenant_perms=tenant_perms,
            is_staff=True,
            is_superuser=False,
        )
    clear_profile_permission_cache(user)
    return count


def clear_model_permissions(*, user, tenant) -> None:
    """Remove all direct user_permissions on the tenant permission row."""
    row = get_tenant_permissions_row(user=user, tenant=tenant)
    if row is None:
        return
    with tenant_context(tenant):
        row.user_permissions.clear()
    clear_profile_permission_cache(user)


def set_tenant_user_permissions(*, user, tenant, permission_ids) -> None:
    """Replace user_permissions M2M in tenant schema."""
    from tenant_users.permissions.models import UserTenantPermissions

    with tenant_context(tenant):
        tenant_perms, _ = UserTenantPermissions.objects.get_or_create(profile=user)
        tenant_perms.user_permissions.set(permission_ids)
    clear_profile_permission_cache(user)


def permissions_queryset_for_tenant(*, tenant, app_labels=None):
    """Permission queryset scoped to tenant schema, optionally filtered by app labels."""
    labels = app_labels or DefaultBusinessPermissionsPolicy.APP_LABELS
    with tenant_context(tenant):
        return Permission.objects.filter(
            content_type__app_label__in=labels
        ).select_related("content_type").order_by(
            "content_type__app_label",
            "content_type__model",
            "codename",
        )


def resolve_permission_ids(*, tenant, perm_specs: list[str]) -> list[int]:
    """
    Resolve permission specs like ``projects.view_project`` to PKs in tenant schema.

    Raises ValueError for unknown specs.
    """
    missing = []
    ids = []
    with tenant_context(tenant):
        for spec in perm_specs:
            spec = spec.strip()
            if not spec or "." not in spec:
                continue
            app_label, codename = spec.split(".", 1)
            perm = Permission.objects.filter(
                content_type__app_label=app_label,
                codename=codename,
            ).first()
            if perm is None:
                missing.append(spec)
            else:
                ids.append(perm.pk)
    if missing:
        raise ValueError(f"Unknown permissions in tenant schema: {', '.join(missing)}")
    return ids


def grant_permissions_by_spec(*, user, tenant, perm_specs: list[str]) -> int:
    """Add permissions by app_label.codename without removing existing grants."""
    from tenant_users.permissions.models import UserTenantPermissions

    new_ids = resolve_permission_ids(tenant=tenant, perm_specs=perm_specs)
    with tenant_context(tenant):
        tenant_perms, _ = UserTenantPermissions.objects.get_or_create(profile=user)
        tenant_perms.user_permissions.add(*new_ids)
    clear_profile_permission_cache(user)
    return len(new_ids)


def revoke_permissions_by_spec(*, user, tenant, perm_specs: list[str]) -> int:
    """Remove permissions by app_label.codename."""
    from tenant_users.permissions.models import UserTenantPermissions

    remove_ids = resolve_permission_ids(tenant=tenant, perm_specs=perm_specs)
    row = get_tenant_permissions_row(user=user, tenant=tenant)
    if row is None:
        return 0
    with tenant_context(tenant):
        row.user_permissions.remove(*remove_ids)
    clear_profile_permission_cache(user)
    return len(remove_ids)
