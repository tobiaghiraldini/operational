from django.contrib import admin
from django.contrib import messages
from django.db import connection
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import NoReverseMatch, path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django_tenants.utils import get_public_schema_name
from django.core.exceptions import PermissionDenied
from unfold.admin import ModelAdmin
from apps.core.admin_mixins import TenantSchemaOnlyAdminMixin
from apps.documents.services.celery_task_result_lookup import (
    fetch_task_result,
    task_result_progress_summary,
)
from apps.documents.forms import DocumentFileAdminForm
from apps.documents.services.document_file_invoice_task import (
    mark_processing_with_task_id as document_file_mark_processing_with_task_id,
)
from apps.documents.storage import document_absolute_path
from .models import DocumentFolder, DocumentFile


@admin.register(DocumentFolder)
class DocumentFolderAdmin(TenantSchemaOnlyAdminMixin, ModelAdmin):
    list_display = [
        'name', 'path', 'is_active', 'auto_process',
        'file_count', 'zip_batch_link', 'created_at'
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

    @admin.display(description="ZIP batch")
    def zip_batch_link(self, obj):
        url = reverse("admin:documents_documentfolder_zip_batch", args=[obj.pk])
        return format_html('<a class="link" href="{}">Upload ZIP…</a>', url)

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            path(
                "<path:object_id>/zip-batch/",
                self.admin_site.admin_view(self.zip_batch_upload_view),
                name="%s_%s_zip_batch" % info,
            ),
        ] + super().get_urls()

    def zip_batch_upload_view(self, request, object_id):
        folder = get_object_or_404(DocumentFolder, pk=object_id)
        if not self.has_change_permission(request, folder):
            raise PermissionDenied

        schema_name = (
            None
            if connection.schema_name == get_public_schema_name()
            else connection.schema_name
        )

        if request.method == "POST":
            zf = request.FILES.get("zip")
            if not zf:
                self.message_user(request, "Choose a ZIP file to upload.", level=messages.ERROR)
            else:
                from apps.files.services.zip_invoice_batch import ingest_zip_invoice_pdfs

                result = ingest_zip_invoice_pdfs(
                    zf,
                    folder=folder,
                    user_id=getattr(request.user, "pk", None),
                    schema_name=schema_name,
                )
                if result.get("success"):
                    n = result.get("queued", 0)
                    self.message_user(
                        request,
                        f"Queued {n} PDF(s) for processing (batch {result.get('batch_id', '')}).",
                        level=messages.SUCCESS,
                    )
                    errs = result.get("errors") or []
                    if errs:
                        self.message_user(
                            request,
                            "Some entries were skipped: " + "; ".join(errs[:5]),
                            level=messages.WARNING,
                        )
                else:
                    self.message_user(
                        request,
                        result.get("error", "ZIP processing failed."),
                        level=messages.ERROR,
                    )
            return HttpResponseRedirect(
                reverse("admin:documents_documentfolder_zip_batch", args=[folder.pk])
            )

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": f"ZIP batch upload — {folder.name}",
            "folder": folder,
        }
        return TemplateResponse(
            request,
            "admin/documents/documentfolder/zip_batch_upload.html",
            context,
        )


@admin.register(DocumentFile)
class DocumentFileAdmin(TenantSchemaOnlyAdminMixin, ModelAdmin):
    form = DocumentFileAdminForm
    list_display = [
        'filename', 'folder', 'file_type', 'file_size_display',
        'status', 'celery_queue_display', 'upload_date', 'processed_at'
    ]
    list_filter = [
        'status', 'file_type', 'folder', 'upload_date', 'processed_at'
    ]
    search_fields = ['filename', 'folder__name']
    readonly_fields = [
        'created_at', 'updated_at', 'upload_date', 'file_hash',
        'file_size', 'legacy_file_path_display',
        'processing_task_id', 'celery_task_detail_display',
    ]
    date_hierarchy = 'upload_date'

    @admin.display(description="Legacy path")
    def legacy_file_path_display(self, obj):
        return obj.file_path or "—"

    @admin.display(description="Celery")
    def celery_queue_display(self, obj):
        tid = (getattr(obj, "processing_task_id", None) or "").strip()
        if not tid:
            return "—"
        tr = fetch_task_result(tid)
        summary = task_result_progress_summary(tr)
        if not summary["found"]:
            return format_html(
                '<span class="text-gray-500" title="Task id: {}">queued…</span>',
                tid[:20],
            )
        st = summary.get("status") or "—"
        pct = summary.get("percent")
        stage = summary.get("stage") or ""
        title = f"{st}" + (f" — {stage}" if stage else "")
        if pct is not None:
            return format_html(
                '<span title="{}">{} ({}%)</span>',
                title,
                st,
                pct,
            )
        return format_html('<span title="{}">{}</span>', title, st)

    @admin.display(description="Celery task (refresh page to update)")
    def celery_task_detail_display(self, obj):
        tid = (getattr(obj, "processing_task_id", None) or "").strip()
        if not tid:
            return "No task id stored yet. Save triggers queue only when auto-process runs."
        tr = fetch_task_result(tid)
        summary = task_result_progress_summary(tr)
        if not summary["found"]:
            return format_html(
                "<p>Task id <code>{}</code> not found in <code>django_celery_results</code> yet. "
                "This lookup uses the <strong>public</strong> schema (not tenant permissions). "
                "Typical causes: worker still queued, different <code>CELERY_RESULT_BACKEND</code> "
                "on worker vs web, or the result row was never persisted. "
                "If the document status already moved to processed/error, refresh once more or "
                "check the worker logs for result-backend errors.</p>",
                tid,
            )
        lines = [
            format_html("<p><strong>State:</strong> {}</p>", summary.get("status")),
        ]
        if summary.get("percent") is not None:
            lines.append(
                format_html(
                    "<p><strong>Progress:</strong> {}%</p>", summary["percent"]
                )
            )
        if summary.get("stage"):
            lines.append(
                format_html("<p><strong>Stage:</strong> {}</p>", summary["stage"])
            )
        if summary.get("date_started"):
            lines.append(
                format_html("<p><strong>Started:</strong> {}</p>", summary["date_started"])
            )
        if summary.get("date_done"):
            lines.append(
                format_html("<p><strong>Finished:</strong> {}</p>", summary["date_done"])
            )
        if summary.get("worker"):
            lines.append(
                format_html("<p><strong>Worker:</strong> {}</p>", summary["worker"])
            )
        if tr is not None:
            try:
                url = reverse(
                    "admin:django_celery_results_taskresult_change",
                    args=[tr.pk],
                )
                lines.append(
                    format_html('<p><a class="link" href="{}">Open task result</a></p>', url)
                )
            except NoReverseMatch:
                lines.append(
                    format_html(
                        "<p><em>Register django_celery_results in admin to link here.</em></p>"
                    )
                )
        return mark_safe("".join(lines))

    fieldsets = (
        ('File Information', {
            'fields': (
                'invoice_storage_kind',
                'folder',
                'file',
                'filename',
                'file_type',
                'file_size',
                'file_hash',
                'legacy_file_path_display',
            ),
            'description': (
                'Leave Folder empty to use the path implied by Invoice storage. '
                'Filename defaults from the upload when left blank.'
            ),
        }),
        ('Processing Status', {
            'fields': (
                'status',
                'processed_at',
                'error_message',
                'processing_task_id',
                'celery_task_detail_display',
            )
        }),
        ('Timestamps', {
            'fields': ('upload_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        from django.db import IntegrityError

        try:
            super().save_model(request, obj, form, change)
        except IntegrityError:
            import uuid

            base = (obj.filename or "file").rsplit(".", 1)
            if len(base) == 2:
                obj.filename = f"{base[0]}_{uuid.uuid4().hex[:8]}.{base[1]}"
            else:
                obj.filename = f"{obj.filename}_{uuid.uuid4().hex[:8]}"
            super().save_model(request, obj, form, change)

        should_queue = (
            obj.folder.auto_process
            and (obj.file_type or '').lower() == 'pdf'
            and obj.file
            and (not change or 'file' in form.changed_data)
        )
        if should_queue:
            from django.db import connection
            from django_tenants.utils import get_public_schema_name

            from apps.invoices.tasks import process_single_invoice

            schema_name = (
                None
                if connection.schema_name == get_public_schema_name()
                else connection.schema_name
            )
            ar = process_single_invoice.delay(
                document_absolute_path(obj),
                obj.filename,
                user_id=getattr(request.user, "pk", None),
                document_file_id=obj.pk,
                schema_name=schema_name,
            )
            document_file_mark_processing_with_task_id(obj.pk, ar.id)
    
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
        from django.db import connection
        from django_tenants.utils import get_public_schema_name

        from apps.invoices.tasks import process_single_invoice

        schema_name = (
            None
            if connection.schema_name == get_public_schema_name()
            else connection.schema_name
        )
        count = 0
        for file_obj in queryset:
            if file_obj.status in ['error', 'pending', 'processing']:
                ar = process_single_invoice.delay(
                    document_absolute_path(file_obj),
                    file_obj.filename,
                    document_file_id=file_obj.pk,
                    schema_name=schema_name,
                )
                document_file_mark_processing_with_task_id(file_obj.pk, ar.id)
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
                    result = processor.process_file(
                        document_absolute_path(file_obj), file_obj.file_type
                    )
                    
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