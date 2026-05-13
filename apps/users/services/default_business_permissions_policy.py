"""Default tenant-business permissions policy.

This policy is intentionally isolated from the admin UI so we can later swap it
for subscription-tier or role-based permission strategies.
"""
from django.contrib.auth.models import Permission


class DefaultBusinessPermissionsPolicy:
    APP_LABELS = (
        "services",
        "dashboard",
        "plans",
        "milestones",
        "products",
        "systems",
        "parts",
        "topics",
        "knowledge",
        "tasks",
        "deadlines",
        "money",
        "accounting",
        "customers",
        "vendors",
        "documents",
        "invoices",
        "organizations",
    )

    def grant(self, *, tenant_perms, is_staff: bool, is_superuser: bool) -> int:
        """Grant default model-level permissions to a tenant permission row.

        Adds every Permission whose content type is in `APP_LABELS` (idempotent
        for duplicates). Re-run after new models ship so existing staff pick up
        new codenames, or use ``sync_default_business_permissions`` management
        command.

        Returns number of permission objects considered for grant.
        """
        if not is_staff or is_superuser:
            return 0
        permissions = Permission.objects.filter(
            content_type__app_label__in=self.APP_LABELS
        )
        tenant_perms.user_permissions.add(*permissions)
        return permissions.count()
