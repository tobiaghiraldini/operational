"""Shared admin mixins."""


class TenantSchemaOnlyAdminMixin:
    """Hide tenant-scoped admins on the public schema.

    Tenant apps (`TENANT_APPS`) do not have their tables in the `public` schema.
    This mixin prevents Django admin from trying to query those tables when a user
    is browsing the public domain.
    """

    @staticmethod
    def _is_public_schema(request) -> bool:
        tenant = getattr(request, "tenant", None)
        schema_name = getattr(tenant, "schema_name", None)
        return schema_name == "public" or schema_name is None

    def has_module_permission(self, request):
        if self._is_public_schema(request):
            return False
        return super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        if self._is_public_schema(request):
            return False
        return super().has_view_permission(request, obj=obj)

    def has_add_permission(self, request):
        if self._is_public_schema(request):
            return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if self._is_public_schema(request):
            return False
        return super().has_change_permission(request, obj=obj)

    def has_delete_permission(self, request, obj=None):
        if self._is_public_schema(request):
            return False
        return super().has_delete_permission(request, obj=obj)


class PublicSchemaOnlyAdminMixin:
    """Expose admin models only on public schema (platform/super-admin area)."""

    @staticmethod
    def _is_public_schema(request) -> bool:
        tenant = getattr(request, "tenant", None)
        schema_name = getattr(tenant, "schema_name", None)
        return schema_name == "public" or schema_name is None

    def has_module_permission(self, request):
        if not self._is_public_schema(request):
            return False
        return super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        if not self._is_public_schema(request):
            return False
        return super().has_view_permission(request, obj=obj)

    def has_add_permission(self, request):
        if not self._is_public_schema(request):
            return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if not self._is_public_schema(request):
            return False
        return super().has_change_permission(request, obj=obj)

    def has_delete_permission(self, request, obj=None):
        if not self._is_public_schema(request):
            return False
        return super().has_delete_permission(request, obj=obj)
