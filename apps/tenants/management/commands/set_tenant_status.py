from django.core.management.base import BaseCommand, CommandError

from apps.tenants.models import Tenant
from apps.tenants.services.lifecycle import activate_tenant, suspend_tenant


class Command(BaseCommand):
    help = "Activate or suspend a tenant by schema_name."

    def add_arguments(self, parser):
        parser.add_argument("schema_name", type=str)
        parser.add_argument("status", choices=["active", "suspended"])

    def handle(self, *args, **options):
        schema_name = options["schema_name"]
        status = options["status"]

        try:
            tenant = Tenant.objects.get(schema_name=schema_name)
        except Tenant.DoesNotExist as exc:
            raise CommandError(f"Tenant not found: {schema_name}") from exc

        if status == "active":
            activate_tenant(tenant)
        else:
            suspend_tenant(tenant)

        self.stdout.write(self.style.SUCCESS(f"{schema_name} set to {status}"))
