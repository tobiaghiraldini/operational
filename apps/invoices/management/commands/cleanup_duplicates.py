from contextlib import nullcontext

from django.core.management.base import BaseCommand
from django.db.models import Count
from django_tenants.utils import schema_context

from apps.invoices.models import Invoice


class Command(BaseCommand):
    help = 'Clean up duplicate invoices'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force cleanup without confirmation'
        )
        parser.add_argument(
            "--schema",
            type=str,
            help="Optional tenant schema name to run cleanup in.",
        )
    
    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]
        schema_name = options.get("schema")

        self.stdout.write("=== Duplicate Invoice Cleanup ===")
        if schema_name:
            self.stdout.write(f"Schema context: {schema_name}")

        context = schema_context(schema_name) if schema_name else nullcontext()
        with context:
            duplicates = Invoice.objects.values('invoice_number', 'vendor').annotate(
                count=Count('id')
            ).filter(count__gt=1)

            if not duplicates.exists():
                self.stdout.write(self.style.SUCCESS("No duplicate invoices found!"))
                return

            self.stdout.write(f"Found {duplicates.count()} duplicate invoice groups:")

            total_to_delete = 0
            duplicate_details = []
            for duplicate in duplicates:
                invoice_number = duplicate["invoice_number"]
                vendor_id = duplicate["vendor"]

                invoices = Invoice.objects.filter(
                    invoice_number=invoice_number,
                    vendor_id=vendor_id
                ).order_by("-created_at")
                vendor_name = invoices.first().vendor.name
                to_delete_count = len(invoices) - 1

                duplicate_details.append({
                    "invoice_number": invoice_number,
                    "vendor_name": vendor_name,
                    "invoices": invoices,
                })
                total_to_delete += to_delete_count
                self.stdout.write(
                    f"  {invoice_number} from {vendor_name}: "
                    f"{len(invoices)} invoices ({to_delete_count} to delete)"
                )

            self.stdout.write(f"\nTotal invoices to delete: {total_to_delete}")
            if dry_run:
                self.stdout.write(self.style.WARNING("DRY RUN - No invoices will be deleted"))
                return

            if not force:
                confirm = input(
                    f"\nAre you sure you want to delete {total_to_delete} duplicate invoices? (yes/no): "
                )
                if confirm.lower() != "yes":
                    self.stdout.write("Cleanup cancelled.")
                    return

            deleted_count = 0
            for detail in duplicate_details:
                invoices = detail["invoices"]
                to_keep = invoices.first()
                to_delete = invoices[1:]
                self.stdout.write(f"Keeping invoice {to_keep.id} ({to_keep.created_at})")
                for invoice in to_delete:
                    self.stdout.write(f"  Deleting invoice {invoice.id} ({invoice.created_at})")
                    invoice.delete()
                    deleted_count += 1

            self.stdout.write(self.style.SUCCESS(f"\nCleanup completed! Deleted {deleted_count} duplicate invoices."))
