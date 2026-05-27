from django.contrib.contenttypes.models import ContentType
from django_tenants.test.cases import FastTenantTestCase

from apps.parts.models import Part
from apps.parts.services import parts_aggregate
from apps.products.models import Product, ProductLicense, ProjectProduct
from apps.projects.models import Project


class ProjectProductSplitTests(FastTenantTestCase):
    @classmethod
    def setup_tenant(cls, tenant):
        from apps.users.models import TenantUser

        owner, _ = TenantUser.objects.get_or_create(
            email="projects-test@example.com",
            defaults={"is_active": True},
        )
        tenant.name = "Projects Test"
        tenant.slug = "projects-test"
        tenant.owner = owner

    def test_project_and_commercial_product_are_distinct(self):
        project = Project.objects.create(
            name="Operational App",
            slug="operational-app",
            status=Project.Status.DEV,
        )
        product = Product.objects.create(
            name="Cursor Pro",
            slug="cursor-pro",
            vendor="Anysphere",
            product_kind=Product.ProductKind.IDE,
        )
        ProjectProduct.objects.create(
            project=project,
            product=product,
            role="IDE",
        )
        license_row = ProductLicense.objects.create(
            product=product,
            license_type=ProductLicense.LicenseType.SUBSCRIPTION,
            status=ProductLicense.Status.ACTIVE,
        )

        self.assertEqual(project.commercial_products.count(), 1)
        self.assertEqual(license_row.product, product)
        self.assertNotEqual(project.pk, product.pk)

    def test_parts_aggregate_on_project(self):
        project = Project.objects.create(name="P", slug="p")
        Part.objects.create(
            content_type=ContentType.objects.get_for_model(Project),
            object_id=project.pk,
            name="token",
            part_type=Part.PartType.TOKEN,
        )
        agg = parts_aggregate(project)
        self.assertEqual(agg["parts"].count(), 1)
