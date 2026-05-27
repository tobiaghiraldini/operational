from django_tenants.test.cases import FastTenantTestCase

from apps.dashboard.services import project_summary_widget_data
from apps.projects.models import Project


class ProjectSummaryWidgetTests(FastTenantTestCase):
    @classmethod
    def setup_tenant(cls, tenant):
        from apps.users.models import TenantUser

        owner, _ = TenantUser.objects.get_or_create(
            email="dashboard-pm-test@example.com",
            defaults={"is_active": True},
        )
        tenant.name = "Dashboard PM Test"
        tenant.slug = "dashboard-pm-test"
        tenant.owner = owner

    def test_empty_summary(self):
        data = project_summary_widget_data()
        self.assertEqual(data["total_projects"], 0)
        self.assertEqual(data["projects"], [])

    def test_includes_project_row(self):
        Project.objects.create(name="App", slug="app", status=Project.Status.LIVE)
        data = project_summary_widget_data()
        self.assertEqual(data["total_projects"], 1)
        self.assertEqual(data["projects"][0]["name"], "App")
