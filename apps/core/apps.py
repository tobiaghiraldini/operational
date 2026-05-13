from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core"

    def ready(self) -> None:
        # Unfold replaces django.contrib.admin.site in unfold.apps; swap in a
        # tenant-aware subclass so public-schema admin never lists tenant-only apps.
        from django.contrib import admin
        from django.contrib.admin import sites as admin_sites

        from apps.core.tenant_admin_site import TenantAwareUnfoldAdminSite
        from unfold.sites import UnfoldAdminSite

        if isinstance(admin.site, TenantAwareUnfoldAdminSite):
            return
        if not isinstance(admin.site, UnfoldAdminSite):
            return

        previous = admin.site
        site = TenantAwareUnfoldAdminSite(name=previous.name)
        site._registry = previous._registry
        admin.site = site
        admin_sites.site = site
