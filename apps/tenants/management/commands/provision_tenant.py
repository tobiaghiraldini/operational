from django.core.management.base import BaseCommand, CommandError
from tenant_users.tenants.models import ExistsError, InactiveError

from apps.tenants.services.provisioning import provision_tenant_for_owner


class Command(BaseCommand):
    help = "Provision a tenant and domain for an owner user."

    def add_arguments(self, parser):
        parser.add_argument("tenant_name", type=str, help="Human-friendly tenant name")
        parser.add_argument("tenant_slug", type=str, help="Tenant slug used for domain provisioning")
        parser.add_argument("owner_email", type=str, help="Owner email (global user)")
        parser.add_argument(
            "--owner-password",
            type=str,
            default=None,
            help="Optional password used when owner user is newly created.",
        )
        parser.add_argument(
            "--no-superuser",
            action="store_true",
            help="Do not grant tenant-level superuser permissions to owner.",
        )
        parser.add_argument(
            "--no-staff",
            action="store_true",
            help="Do not grant tenant-level staff permissions to owner.",
        )

    def handle(self, *args, **options):
        try:
            result = provision_tenant_for_owner(
                tenant_name=options["tenant_name"],
                tenant_slug=options["tenant_slug"],
                owner_email=options["owner_email"],
                owner_password=options["owner_password"],
                is_superuser=not options["no_superuser"],
                is_staff=not options["no_staff"],
            )
        except ExistsError as exc:
            raise CommandError(f"Tenant/domain already exists: {exc}") from exc
        except InactiveError as exc:
            raise CommandError(f"Owner user is inactive: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"Tenant creation failed: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Tenant created successfully: "
                f"schema={result.tenant_schema} "
                f"domain={result.domain_url} "
                f"owner={result.owner_email}"
            )
        )
