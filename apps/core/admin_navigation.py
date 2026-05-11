"""Unfold sidebar navigation configuration."""

from django.urls import reverse_lazy


def _is_public_super_admin(request) -> bool:
    tenant = getattr(request, "tenant", None)
    is_public_schema = getattr(tenant, "schema_name", None) in (None, "public")
    return bool(is_public_schema and request.user.is_superuser)


def get_sidebar_navigation(request):
    """Return grouped/collapsible app navigation for Unfold sidebar."""

    return [
        {
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
        },
        {
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
        },
        {
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
        },
        {
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
                    "link": reverse_lazy("admin:permissions_usertenantpermissions_changelist"),
                    "permission": _is_public_super_admin,
                },
            ],
        },
    ]
