from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    verbose_name = "Users"

    def ready(self):
        from tenant_users.permissions.models import UserTenantPermissions

        profile_field = UserTenantPermissions._meta.get_field("profile")
        profile_field.db_constraint = False
