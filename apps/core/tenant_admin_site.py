"""Admin site that hides tenant-schema models from the public schema UI."""

from functools import lru_cache

from django.apps import apps as django_apps
from django.conf import settings
from django.http import HttpRequest
from unfold.sites import UnfoldAdminSite

from apps.core.tenant_schema import is_public_schema


@lru_cache(maxsize=1)
def _tenant_only_app_labels() -> frozenset[str]:
    """App labels whose models live only in tenant schemas (not in public)."""
    shared = frozenset(settings.SHARED_APPS)
    tenant_only_paths = frozenset(
        name for name in settings.TENANT_APPS if name not in shared
    )
    labels: set[str] = set()
    for cfg in django_apps.get_app_configs():
        if cfg.name in tenant_only_paths:
            labels.add(cfg.label)
    return frozenset(labels)


class TenantAwareUnfoldAdminSite(UnfoldAdminSite):
    """Unfold admin site that omits tenant-only apps when serving the public schema."""

    def _build_app_dict(self, request: HttpRequest, label=None):
        app_dict = super()._build_app_dict(request, label)
        if not is_public_schema():
            return app_dict
        hidden = _tenant_only_app_labels()
        return {k: v for k, v in app_dict.items() if k not in hidden}
