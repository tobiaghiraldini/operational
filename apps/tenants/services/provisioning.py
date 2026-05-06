from __future__ import annotations

from dataclasses import dataclass

from tenant_users.tenants.models import ExistsError
from tenant_users.tenants.tasks import provision_tenant
from tenant_users.tenants.utils import create_public_tenant

from apps.users.models import TenantUser


@dataclass(frozen=True)
class TenantProvisioningResult:
    tenant_schema: str
    domain_url: str
    owner_email: str


def bootstrap_public_tenant(domain_url: str, owner_email: str) -> TenantProvisioningResult:
    """
    Ensure the public tenant exists and is owned by the given user email.
    Safe to call repeatedly in local/dev bootstrap flows.
    """
    try:
        tenant, domain, owner = create_public_tenant(
            domain_url=domain_url,
            owner_email=owner_email,
            is_superuser=True,
            is_staff=True,
        )
    except ExistsError:
        from apps.tenants.models import Tenant

        tenant = Tenant.objects.get(schema_name="public")
        domain = tenant.domains.filter(is_primary=True).first() or tenant.domains.first()
        owner = tenant.owner
    return TenantProvisioningResult(
        tenant_schema=tenant.schema_name,
        domain_url=domain.domain if domain else domain_url,
        owner_email=owner.email,
    )


def provision_tenant_for_owner(
    tenant_name: str,
    tenant_slug: str,
    owner_email: str,
    *,
    owner_password: str | None = None,
    is_superuser: bool = True,
    is_staff: bool = True,
) -> TenantProvisioningResult:
    """
    Create a global user (if needed) and provision a new tenant + domain.
    """
    owner, created = TenantUser.objects.get_or_create(email=owner_email)
    if created and owner_password:
        owner.set_password(owner_password)
        owner.save(update_fields=["password", "updated_at"])

    tenant, domain = provision_tenant(
        tenant_name=tenant_name,
        tenant_slug=tenant_slug,
        owner=owner,
        is_superuser=is_superuser,
        is_staff=is_staff,
    )
    return TenantProvisioningResult(
        tenant_schema=tenant.schema_name,
        domain_url=domain.domain,
        owner_email=owner.email,
    )
