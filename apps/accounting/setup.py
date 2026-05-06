"""Tenant-level setup wizard gating for the accounting feature.

Decision recorded in `.cursor/plans/accounting-min-features_*.plan.md`:
provisioning stays untouched. Each tenant must pick a base currency and create
at least one `money.Account` before they can use the accounting views.
"""
from __future__ import annotations

from typing import Iterable

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import wraps

SETUP_FLAG_KEY = "accounting_setup_completed_at"


def is_setup_completed(request: HttpRequest) -> bool:
    """True when the current tenant has completed the accounting wizard."""
    tenant = getattr(request, "tenant", None)
    if tenant is None:
        return False
    if not getattr(tenant, "settings_json", None):
        return False
    if not tenant.settings_json.get(SETUP_FLAG_KEY):
        return False
    return _has_required_data()


def _has_required_data() -> bool:
    from apps.money.models import Account, Currency

    if not Currency.objects.filter(is_active=True).exists():
        return False
    return Account.objects.filter(is_active=True).exists()


def mark_setup_completed(request: HttpRequest) -> None:
    """Persist the completion flag on the current tenant's settings_json."""
    tenant = getattr(request, "tenant", None)
    if tenant is None:
        return
    tenant.settings_json = tenant.settings_json or {}
    tenant.settings_json[SETUP_FLAG_KEY] = timezone.now().isoformat()
    tenant.save(update_fields=["settings_json"])


def accounting_setup_required(view_func):
    """Decorator that redirects to the wizard until setup is complete."""

    @wraps(view_func)
    @login_required
    def _wrapper(request: HttpRequest, *args, **kwargs):
        if is_setup_completed(request):
            return view_func(request, *args, **kwargs)
        return redirect(reverse("accounting:setup_intro"))

    return _wrapper


def get_base_currency(request: HttpRequest) -> str:
    """Return the tenant's base currency (defaults to "EUR" when missing)."""
    tenant = getattr(request, "tenant", None)
    if tenant is not None and getattr(tenant, "currency", None):
        return tenant.currency
    return "EUR"


def setup_steps() -> Iterable[dict]:
    return (
        {"slug": "currency", "title": "Base currency"},
        {"slug": "accounts", "title": "Accounts"},
        {"slug": "review", "title": "Review"},
    )
