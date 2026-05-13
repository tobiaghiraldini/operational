"""Dump selected tenant-schema models to JSON for ``loaddata`` (dev snapshots)."""
from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import get_public_schema_name, schema_context

from apps.tenants.models import Tenant

# Order roughly respects FK dependencies; adjust if loaddata reports cycles.
DEFAULT_LABELS = [
    "vendors.PaymentMethod",
    "vendors.Vendor",
    "customers.Customer",
    "money.Currency",
    "money.Account",
    "money.TransactionCategory",
    "money.ExchangeRate",
    "money.Transaction",
    "money.InvoiceSettlementAllocation",
    "documents.DocumentFile",
    "invoices.Invoice",
    "invoices.InvoiceExtraction",
]


class Command(BaseCommand):
    help = (
        "Write a JSON fixture for one tenant schema (money + invoices + related rows). "
        "Restore with: python manage.py load_tenant_fixture <schema> <file>"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--schema",
            required=True,
            help="Tenant schema_name (see Tenants admin or Tenant.schema_name).",
        )
        parser.add_argument(
            "-o",
            "--output",
            default="",
            help="Output file path. If omitted, writes to stdout.",
        )
        parser.add_argument(
            "--models",
            default="",
            help=f"Comma-separated app labels (default: built-in list of {len(DEFAULT_LABELS)} models).",
        )

    def handle(self, *args, **options):
        schema = options["schema"]
        output = (options.get("output") or "").strip()
        raw_models = (options.get("models") or "").strip()

        public = get_public_schema_name()
        with schema_context(public):
            if not Tenant.objects.filter(schema_name=schema).exists():
                raise CommandError(
                    f"No tenant with schema_name={schema!r} (checked in {public!r} schema)."
                )

        labels = (
            [m.strip() for m in raw_models.split(",") if m.strip()]
            if raw_models
            else DEFAULT_LABELS
        )

        with schema_context(schema):
            if output:
                with open(output, "w", encoding="utf-8") as fh:
                    call_command("dumpdata", *labels, indent=2, stdout=fh)
            else:
                call_command("dumpdata", *labels, indent=2, stdout=self.stdout)

        self.stdout.write(
            self.style.SUCCESS(f"Fixture written: {output or 'stdout'}")
        )
