"""Grant or revoke tenant-scoped permissions for a user by app_label.codename."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.tenants.models import Tenant
from apps.users.models import TenantUser
from apps.users.services.default_business_permissions_policy import (
    DefaultBusinessPermissionsPolicy,
)
from apps.users.services.tenant_permissions_admin import (
    apply_default_business_permissions,
    clear_model_permissions,
    grant_permissions_by_spec,
    revoke_permissions_by_spec,
)


class Command(BaseCommand):
    help = (
        "Grant or revoke permissions on a user's UserTenantPermissions row "
        "in a tenant schema (not the public schema)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--schema",
            required=True,
            help="Tenant schema name (e.g. acme).",
        )
        parser.add_argument(
            "--email",
            required=True,
            help="TenantUser email.",
        )
        parser.add_argument(
            "--grant",
            default="",
            help="Comma-separated permissions: app_label.codename",
        )
        parser.add_argument(
            "--revoke",
            default="",
            help="Comma-separated permissions to remove.",
        )
        parser.add_argument(
            "--apply-defaults",
            action="store_true",
            help="Grant all DefaultBusinessPermissionsPolicy APP_LABELS permissions.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove all direct user_permissions (does not change is_staff).",
        )

    def handle(self, *args, **options):
        schema = options["schema"]
        email = options["email"]

        try:
            tenant = Tenant.objects.get(schema_name=schema)
        except Tenant.DoesNotExist as exc:
            raise CommandError(f"Unknown tenant schema: {schema}") from exc

        try:
            user = TenantUser.objects.get(email=email)
        except TenantUser.DoesNotExist as exc:
            raise CommandError(f"Unknown user: {email}") from exc

        if not user.tenants.filter(pk=tenant.pk).exists():
            raise CommandError(
                f"{email} is not a member of tenant {schema}. "
                "Add membership via TenantUser admin first."
            )

        if options["clear"]:
            clear_model_permissions(user=user, tenant=tenant)
            self.stdout.write(self.style.WARNING(f"Cleared model permissions for {email} on {schema}"))

        if options["apply_defaults"]:
            n = apply_default_business_permissions(user=user, tenant=tenant)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Applied default business permissions ({n} permission rows in policy) on {schema}"
                )
            )

        grant_specs = [s.strip() for s in options["grant"].split(",") if s.strip()]
        if grant_specs:
            try:
                n = grant_permissions_by_spec(user=user, tenant=tenant, perm_specs=grant_specs)
            except ValueError as exc:
                raise CommandError(str(exc)) from exc
            self.stdout.write(self.style.SUCCESS(f"Granted {n} permission(s) on {schema}"))

        revoke_specs = [s.strip() for s in options["revoke"].split(",") if s.strip()]
        if revoke_specs:
            try:
                n = revoke_permissions_by_spec(user=user, tenant=tenant, perm_specs=revoke_specs)
            except ValueError as exc:
                raise CommandError(str(exc)) from exc
            self.stdout.write(self.style.SUCCESS(f"Revoked {n} permission(s) on {schema}"))

        if not any(
            [
                options["clear"],
                options["apply_defaults"],
                grant_specs,
                revoke_specs,
            ]
        ):
            self.stdout.write(
                "No action specified. Use --apply-defaults, --grant, --revoke, and/or --clear."
            )
            self.stdout.write(f"Policy APP_LABELS: {', '.join(DefaultBusinessPermissionsPolicy.APP_LABELS)}")
