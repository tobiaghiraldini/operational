"""Load a JSON fixture produced by ``dump_tenant_fixture`` into one tenant schema."""
from __future__ import annotations

from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import get_public_schema_name, schema_context

from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = (
        "Load a fixture JSON file into a tenant schema (use data from dump_tenant_fixture). "
        "Does not replace the whole database — only inserts/updates from the fixture."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "schema",
            type=str,
            help="Tenant schema_name to load into.",
        )
        parser.add_argument(
            "fixture",
            type=str,
            help="Path to JSON fixture file.",
        )

    def handle(self, *args, **options):
        schema = options["schema"]
        fixture = Path(options["fixture"]).expanduser()
        if not fixture.is_file():
            raise CommandError(f"Fixture not found: {fixture}")

        public = get_public_schema_name()
        with schema_context(public):
            if not Tenant.objects.filter(schema_name=schema).exists():
                raise CommandError(
                    f"No tenant with schema_name={schema!r} (checked in {public!r} schema)."
                )

        with schema_context(schema):
            call_command(
                "loaddata",
                str(fixture),
                ignorenonexistent=True,
            )

        self.stdout.write(
            self.style.SUCCESS(f"Loaded {fixture} into tenant schema {schema!r}.")
        )
