from django.contrib import admin
from .models import DocumentFolder, DocumentFile
from unfold.admin import ModelAdmin
from apps.core.admin_mixins import TenantSchemaOnlyAdminMixin


@admin.register(DocumentFolder)
class DocumentFolderAdmin(TenantSchemaOnlyAdminMixin, ModelAdmin):
    list_display = [
        'name', 'path', 'is_active', 'auto_process', 
        'file_count', 'created_at'
    ]
    list_filter = ['is_active', 'auto_process', 'created_at']
    search_fields = ['name', 'path', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'path', 'description')
        }),
        ('Processing Settings', {
            'fields': ('is_active', 'auto_process')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def file_count(self, obj):
        return obj.files.count()
    file_count.short_description = 'Files'


@admin.register(DocumentFile)
class DocumentFileAdmin(TenantSchemaOnlyAdminMixin, ModelAdmin):
    list_display = [
        'filename', 'folder', 'file_type', 'file_size_display', 
        'status', 'upload_date', 'processed_at'
    ]
    list_filter = [
        'status', 'file_type', 'folder', 'upload_date', 'processed_at'
    ]
    search_fields = ['filename', 'file_path', 'folder__name']
    readonly_fields = [
        'created_at', 'updated_at', 'upload_date', 'file_hash'
    ]
    date_hierarchy = 'upload_date'
    
    fieldsets = (
        ('File Information', {
            'fields': (
                'filename', 'folder', 'file_path', 'file_type',
                'file_size', 'file_hash'
            )
        }),
        ('Processing Status', {
            'fields': ('status', 'processed_at', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('upload_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        size = obj.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    file_size_display.short_description = 'Size'
    
    actions = ['retry_processing', 'mark_as_skipped', 'process_with_ocr']
    
    def retry_processing(self, request, queryset):
        from apps.invoices.tasks import process_single_invoice
        count = 0
        for file_obj in queryset:
            if file_obj.status in ['error', 'pending']:
                process_single_invoice.delay(file_obj.file_path, file_obj.filename)
                file_obj.status = 'pending'
                file_obj.error_message = ''
                file_obj.save()
                count += 1
        self.message_user(request, f'{count} files queued for reprocessing.')
    retry_processing.short_description = 'Retry processing for selected files'
    
    def mark_as_skipped(self, request, queryset):
        updated = queryset.update(status='skipped')
        self.message_user(request, f'{updated} files marked as skipped.')
    mark_as_skipped.short_description = 'Mark selected files as skipped'
    
    def process_with_ocr(self, request, queryset):
        """Process documents using the OCR processor."""
        from apps.documents.ocr import OCRProcessor
        from apps.documents.parser import DocumentParser
        from django.utils import timezone
        
        processor = OCRProcessor()
        parser = DocumentParser()
        count = 0
        
        for file_obj in queryset:
            if file_obj.status not in ['processed']:
                file_obj.status = 'processing'
                file_obj.save()
                
                try:
                    # Extract text
                    result = processor.process_file(file_obj.file_path, file_obj.file_type)
                    
                    if result.get('success'):
                        # Parse data
                        parsed = parser.parse_invoice_data(result.get('text', ''))
                        
                        # Save to DocumentFile (or create Invoice if needed)
                        # This is a simplified version - you might want to create Invoice records here
                        file_obj.status = 'processed'
                        file_obj.processed_at = timezone.now()
                        file_obj.save()
                        count += 1
                    else:
                        file_obj.status = 'error'
                        file_obj.error_message = result.get('error', 'Unknown error')
                        file_obj.save()
                except Exception as e:
                    file_obj.status = 'error'
                    file_obj.error_message = str(e)
                    file_obj.save()
        
        self.message_user(request, f'{count} files processed with OCR.')
    process_with_ocr.short_description = 'Process with OCR and parser'