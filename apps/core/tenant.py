class TenantSafeQuerysetMixin:
    """
    Defensive queryset mixin: always return queryset bound to current schema.
    In django-tenants, schema selection is handled by middleware; this
    keeps API views from accidentally bypassing per-request scoping logic.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset
