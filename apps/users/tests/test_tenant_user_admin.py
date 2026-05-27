from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase

from apps.users.admin import TenantUserAdmin, TenantUserChangeForm, TenantUserCreationForm
from apps.users.models import TenantUser


class TenantUserAdminFormTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = TenantUserAdmin(TenantUser, self.site)
        self.request = RequestFactory().get("/admin/users/tenantuser/add/")

    def test_add_view_uses_creation_form_with_password_fields(self):
        form_class = self.admin.get_form(self.request, obj=None, change=False)
        self.assertTrue(issubclass(form_class, TenantUserCreationForm))
        self.assertIn("password1", form_class.base_fields)
        self.assertIn("password2", form_class.base_fields)
        self.assertIn("managed_tenants", form_class.base_fields)

    def test_change_view_uses_change_form_without_password_fields(self):
        user = TenantUser(email="existing@example.com")
        form_class = self.admin.get_form(self.request, obj=user, change=True)
        self.assertTrue(issubclass(form_class, TenantUserChangeForm))
        self.assertNotIn("password1", form_class.base_fields)
        self.assertNotIn("password2", form_class.base_fields)

    def test_add_fieldsets_include_password_fields(self):
        fieldsets = self.admin.get_fieldsets(self.request, obj=None)
        fields = {name for _title, opts in fieldsets for name in opts["fields"]}
        self.assertIn("password1", fields)
        self.assertIn("password2", fields)

    def test_get_deleted_objects_does_not_query_tenant_tables(self):
        user = TenantUser(email="delete-preview@example.com")
        user.pk = 999
        to_delete, model_count, perms_needed, protected = self.admin.get_deleted_objects(
            [user], self.request
        )
        self.assertEqual(len(to_delete), 2)
        self.assertEqual(model_count["Tenant users"], 1)
        self.assertEqual(perms_needed, set())
        self.assertEqual(protected, [])
