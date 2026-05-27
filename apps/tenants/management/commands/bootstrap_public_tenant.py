from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.tenants.services.provisioning import (
    bootstrap_public_tenant,
    ensure_public_tenant_domain,
)


class Command(BaseCommand):
    help = (
        "Create the public tenant (if missing) and map a domain to it. "
        "Run once on a new server before serving the landing page."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            type=str,
            default=None,
            help=(
                "Public tenant domain (default: TENANT_USERS_DOMAIN from settings, "
                "then operational.cloud)."
            ),
        )
        parser.add_argument(
            "--owner-email",
            type=str,
            default=None,
            help="Owner email for the public tenant admin user (required on first run).",
        )

    def handle(self, *args, **options):
        domain = (
            options["domain"]
            or getattr(settings, "TENANT_USERS_DOMAIN", None)
            or "operational.cloud"
        )
        owner_email = options["owner_email"]
        if not owner_email:
            raise CommandError(
                "Pass --owner-email (e.g. admin@operational.cloud). "
                "Required when creating the public tenant for the first time."
            )

        try:
            result = bootstrap_public_tenant(domain_url=domain, owner_email=owner_email)
            ensure_public_tenant_domain(domain)
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"Public tenant bootstrap failed: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Public tenant ready: "
                f"schema={result.tenant_schema} "
                f"domain={domain} "
                f"owner={result.owner_email}"
            )
        )
