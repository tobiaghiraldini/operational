"""ForeignKey helper for references to the public-schema TenantUser model."""
from django.conf import settings
from django.db import models


def TenantUserForeignKey(**kwargs):
    """Reference AUTH_USER_MODEL from tenant schemas (no cross-schema DB constraint)."""
    kwargs.setdefault("to", settings.AUTH_USER_MODEL)
    kwargs.setdefault("db_constraint", False)
    return models.ForeignKey(**kwargs)
