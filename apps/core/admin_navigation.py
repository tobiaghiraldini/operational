"""Unfold sidebar navigation configuration."""

from django.urls import reverse_lazy

from apps.core.tenant_schema import is_public_schema


def _is_public_super_admin(request) -> bool:
    return bool(is_public_schema() and request.user.is_superuser)


def sidebar_show_all_applications(request):
    """Unfold SIDEBAR.show_all_applications callback (see Unfold configuration docs)."""
    return not is_public_schema()


def _workspace_group():
    return {
        "title": "Workspace",
        "separator": True,
        "collapsible": True,
        "items": [
            {
                "title": "Dashboard",
                "icon": "space_dashboard",
                "link": reverse_lazy("admin:index"),
            },
        ],
    }


def _accounting_finance_group():
    return {
        "title": "Accounting & Finance",
        "separator": True,
        "collapsible": True,
        "items": [
            {
                "title": "Transactions",
                "icon": "account_balance_wallet",
                "link": reverse_lazy("admin:money_transaction_changelist"),
            },
            {
                "title": "Accounts",
                "icon": "account_balance",
                "link": reverse_lazy("admin:money_account_changelist"),
            },
            {
                "title": "Fiscal periods",
                "icon": "calendar_month",
                "link": reverse_lazy("admin:accounting_fiscalperiod_changelist"),
            },
            {
                "title": "Daybooks",
                "icon": "book",
                "link": reverse_lazy("admin:accounting_daybook_changelist"),
            },
            {
                "title": "Period balances",
                "icon": "monitoring",
                "link": reverse_lazy(
                    "admin:accounting_periodaccountbalance_changelist"
                ),
            },
        ],
    }


def _business_group():
    return {
        "title": "Business",
        "separator": True,
        "collapsible": True,
        "items": [
            {
                "title": "Customers",
                "icon": "group",
                "link": reverse_lazy("admin:customers_customer_changelist"),
            },
            {
                "title": "Vendors",
                "icon": "storefront",
                "link": reverse_lazy("admin:vendors_vendor_changelist"),
            },
            {
                "title": "Invoices",
                "icon": "receipt_long",
                "link": reverse_lazy("admin:invoices_invoice_changelist"),
            },
            {
                "title": "Documents",
                "icon": "description",
                "link": reverse_lazy("admin:documents_documentfile_changelist"),
            },
        ],
    }


def _platform_group():
    return {
        "title": "Platform",
        "separator": True,
        "collapsible": True,
        "items": [
            {
                "title": "Tenants",
                "icon": "domain",
                "link": reverse_lazy("admin:tenants_tenant_changelist"),
                "permission": _is_public_super_admin,
            },
            {
                "title": "Domains",
                "icon": "language",
                "link": reverse_lazy("admin:tenants_domain_changelist"),
                "permission": _is_public_super_admin,
            },
            {
                "title": "Users",
                "icon": "manage_accounts",
                "link": reverse_lazy("admin:users_tenantuser_changelist"),
                "permission": _is_public_super_admin,
            },
            {
                "title": "Tenant permissions",
                "icon": "admin_panel_settings",
                "link": reverse_lazy(
                    "admin:permissions_usertenantpermissions_changelist"
                ),
                "permission": _is_public_super_admin,
            },
        ],
    }


def get_sidebar_navigation(request):
    """Return grouped/collapsible app navigation for Unfold sidebar."""
    if is_public_schema():
        return [_workspace_group(), _platform_group()]
    return [
        _workspace_group(),
        _accounting_finance_group(),
        _business_group(),
        _platform_group(),
    ]
