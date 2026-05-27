from django_tenants.test.cases import FastTenantTestCase

from apps.users.services.default_business_permissions_policy import (
    DefaultBusinessPermissionsPolicy,
)


class DefaultBusinessPermissionsPolicyTests(FastTenantTestCase):
    @classmethod
    def setup_tenant(cls, tenant):
        from apps.users.models import TenantUser

        owner, _ = TenantUser.objects.get_or_create(
            email="policy-test@example.com",
            defaults={"is_active": True},
        )
        tenant.name = "Policy Test"
        tenant.slug = "policy-test"
        tenant.owner = owner

    def test_pm_apps_in_app_labels(self):
        labels = DefaultBusinessPermissionsPolicy.APP_LABELS
        for app in (
            "projects",
            "issues",
            "architecture",
            "stack",
            "testing",
            "operations",
            "checks",
            "solutions",
        ):
            self.assertIn(app, labels)
