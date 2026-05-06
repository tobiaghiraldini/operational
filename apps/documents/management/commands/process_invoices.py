from django.core.management.base import BaseCommand, CommandError
from pathlib import Path
from contextlib import nullcontext
from django_tenants.utils import schema_context
from apps.invoices.tasks import process_document_folder
from apps.documents.models import DocumentFolder, DocumentFile
from apps.invoices.tasks import calculate_file_hash


class Command(BaseCommand):
    help = 'Process all PDF invoices in specified folders'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'folder_path', 
            type=str, 
            help='Path to invoices folder'
        )
        parser.add_argument(
            '--create-folder-record',
            action='store_true',
            help='Create a DocumentFolder record for this path'
        )
        parser.add_argument(
            '--auto-process',
            action='store_true',
            help='Enable auto-processing for this folder'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually processing'
        )
        parser.add_argument(
            "--schema",
            type=str,
            help="Optional tenant schema name to run processing in.",
        )
    
    def handle(self, *args, **options):
        folder_path = Path(options['folder_path'])
        schema_name = options.get("schema")
        context = schema_context(schema_name) if schema_name else nullcontext()
        if schema_name:
            self.stdout.write(f"Running in schema: {schema_name}")

        with context:
            self._process_folder(folder_path, options)

    def _process_folder(self, folder_path: Path, options: dict):
        
        if not folder_path.exists():
            raise CommandError(f"Folder {folder_path} does not exist")
        
        if not folder_path.is_dir():
            raise CommandError(f"Path {folder_path} is not a directory")
        
        # Create folder record if requested
        if options["create_folder_record"]:
            folder_record, created = DocumentFolder.objects.get_or_create(
                path=str(folder_path.absolute()),
                defaults={
                    'name': folder_path.name,
                    'description': f'Auto-created folder for {folder_path.name}',
                    'auto_process': options["auto_process"]
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created folder record: {folder_record.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Folder record already exists: {folder_record.name}')
                )
        
        # Find PDF files
        pdf_files = list(folder_path.glob('**/*.pdf'))
        self.stdout.write(f"Found {len(pdf_files)} PDF files in {folder_path}")
        
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN - No files will be processed"))
            for pdf_file in pdf_files:
                self.stdout.write(f"  Would process: {pdf_file.name}")
            return
        
        # Process files
        processed_count = 0
        skipped_count = 0
        error_count = 0
        
        for pdf_file in pdf_files:
            try:
                # Check if already processed
                file_hash = calculate_file_hash(str(pdf_file))
                if DocumentFile.objects.filter(file_hash=file_hash).exists():
                    self.stdout.write(
                        self.style.WARNING(f"Skipping already processed: {pdf_file.name}")
                    )
                    skipped_count += 1
                    continue
                
                # Queue for processing
                result = process_document_folder.delay(
                    str(pdf_file.parent),
                    schema_name=options.get("schema"),
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Queued for processing: {pdf_file.name}")
                )
                processed_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing {pdf_file.name}: {str(e)}")
                )
                error_count += 1
        
        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write("PROCESSING SUMMARY")
        self.stdout.write("="*50)
        self.stdout.write(f"Total files found: {len(pdf_files)}")
        self.stdout.write(f"Files queued: {processed_count}")
        self.stdout.write(f"Files skipped: {skipped_count}")
        self.stdout.write(f"Errors: {error_count}")
        
        if processed_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n{processed_count} files have been queued for processing. "
                    "Check the admin interface or Celery logs for progress."
                )
            )


