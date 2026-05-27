from django.conf import settings
from django.db import connection
from django.test import TestCase
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context

from apps.users.models import TenantUser


class TenantSchemaMigrationTests(TenantTestCase):
    """Ensure new tenant schemas get contenttypes before tenant app migrations."""

    @classmethod
    def get_test_schema_name(cls):
        return "test_tenant_migrations"

    @classmethod
    def get_test_tenant_domain(cls):
        return "test-tenant-migrations.test.com"

    @classmethod
    def setup_tenant(cls, tenant):
        owner, _ = TenantUser.objects.get_or_create(
            email="tenant-migration-test@example.com",
            defaults={"is_active": True},
        )
        tenant.name = "Migration Test Tenant"
        tenant.slug = "migration-test"
        tenant.owner = owner

    @classmethod
    def tearDownClass(cls):
        """Drop schema and public rows without ORM cascade into tenant-schema tables."""
        connection.set_schema_to_public()
        schema_name = cls.tenant.schema_name
        domain_pk = cls.domain.pk
        tenant_pk = cls.tenant.pk
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
            cursor.execute("DELETE FROM tenants_domain WHERE id = %s", [domain_pk])
            cursor.execute("DELETE FROM tenants_tenant WHERE id = %s", [tenant_pk])
        cls.remove_allowed_test_domain()

    def test_contenttypes_table_exists_in_tenant_schema(self):
        with schema_context(self.tenant.schema_name):
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = 'django_content_type'
                    """,
                    [self.tenant.schema_name],
                )
                self.assertIsNotNone(cursor.fetchone())

    def test_parts_table_exists_in_tenant_schema(self):
        with schema_context(self.tenant.schema_name):
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = 'parts_part'
                    """,
                    [self.tenant.schema_name],
                )
                self.assertIsNotNone(cursor.fetchone())


class TenantAppsConfigurationTests(TestCase):
    """Guardrail: tenant models must not rely on shared-only Django contrib tables."""

    def test_contenttypes_and_auth_are_tenant_apps(self):
        tenant_apps = set(settings.TENANT_APPS)
        self.assertIn("django.contrib.contenttypes", tenant_apps)
        self.assertIn("django.contrib.auth", tenant_apps)
