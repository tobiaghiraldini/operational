from apps.tenants.models import Tenant


def activate_tenant(tenant: Tenant) -> Tenant:
    tenant.status = Tenant.STATUS_ACTIVE
    tenant.suspended_at = None
    tenant.save(update_fields=["status", "suspended_at", "updated_at"])
    return tenant


def suspend_tenant(tenant: Tenant) -> Tenant:
    from django.utils import timezone

    tenant.status = Tenant.STATUS_SUSPENDED
    tenant.suspended_at = timezone.now()
    tenant.save(update_fields=["status", "suspended_at", "updated_at"])
    return tenant
