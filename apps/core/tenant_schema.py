"""Helpers for distinguishing the public (shared) PostgreSQL schema from tenant schemas."""

from django.db import connection
from django_tenants.utils import get_public_schema_name


def is_public_schema() -> bool:
    """True when the current DB connection is on the public schema."""
    return connection.schema_name == get_public_schema_name()
