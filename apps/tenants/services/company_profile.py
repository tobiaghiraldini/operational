"""Resolve tenant company profile (`organizations.Organization`) for invoice flows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from django.db import connection
from django_tenants.utils import get_public_schema_name

if TYPE_CHECKING:
    from apps.organizations.models import Organization


def _restore_connection_schema(schema_name: str) -> None:
    public = get_public_schema_name()
    if schema_name == public:
        connection.set_schema_to_public()
    else:
        connection.set_schema(schema_name, include_public=False)


def fetch_tenant_company_profile_for_schema(schema_name: str | None) -> Optional["Organization"]:
    """
    Load the optional Organization (company profile) for the tenant with this schema.

    Organization rows live in the tenant schema; the Tenant row lives in public.
    Restores the connection schema after the lookup.
    """
    if not schema_name or schema_name == get_public_schema_name():
        return None

    from apps.organizations.models import Organization
    from apps.tenants.models import Tenant

    previous = connection.schema_name
    tenant_pk = None
    connection.set_schema_to_public()
    try:
        tenant = Tenant.objects.filter(schema_name=schema_name).first()
        if tenant is not None:
            tenant_pk = tenant.pk
    finally:
        _restore_connection_schema(schema_name)

    if tenant_pk is None:
        _restore_connection_schema(previous)
        return None

    try:
        return Organization.objects.filter(tenant_id=tenant_pk).first()
    finally:
        _restore_connection_schema(previous)
