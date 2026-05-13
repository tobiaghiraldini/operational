"""Forms for document admin and uploads."""

from __future__ import annotations

from django import forms
from django.conf import settings

from apps.documents.folder_paths import (
    STORAGE_KIND_CHOICES,
    STORAGE_KIND_RECEIVED,
    folder_for_storage_kind,
    sanitize_upload_filename,
    unique_filename_for_folder,
)
from apps.documents.models import DocumentFile


class DocumentFileAdminForm(forms.ModelForm):
    """Admin create/change: upload ``file``; folder/filename optional with smart defaults."""

    invoice_storage_kind = forms.ChoiceField(
        label="Invoice storage",
        choices=STORAGE_KIND_CHOICES,
        initial=STORAGE_KIND_RECEIVED,
        required=False,
        help_text=(
            "Targets MEDIA folders invoices/received, invoices/emitted, or invoices/bulk "
            "when Folder is left empty."
        ),
    )

    class Meta:
        model = DocumentFile
        fields = (
            "invoice_storage_kind",
            "folder",
            "file",
            "filename",
            "file_type",
            "status",
            "processed_at",
            "error_message",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["folder"].required = False
        self.fields["filename"].required = False
        if self.instance.pk:
            self.fields["file"].required = False
            self.fields["invoice_storage_kind"].widget = forms.HiddenInput()
            self.fields["invoice_storage_kind"].required = False

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if not f:
            return f
        max_b = getattr(settings, "INVOICE_MAX_UPLOAD_BYTES", 25 * 1024 * 1024)
        if getattr(f, "size", 0) and f.size > max_b:
            raise forms.ValidationError(
                f"File exceeds maximum size ({max_b} bytes)."
            )
        return f

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned

        is_add = not self.instance.pk
        upload = cleaned.get("file")
        kind = (cleaned.get("invoice_storage_kind") or STORAGE_KIND_RECEIVED).strip().lower()

        if is_add and not upload:
            raise forms.ValidationError({"file": "An uploaded file is required."})

        folder = cleaned.get("folder")
        if not folder:
            if self.instance.pk and self.instance.folder_id:
                folder = self.instance.folder
                cleaned["folder"] = folder
            else:
                folder, _ = folder_for_storage_kind(kind)
                cleaned["folder"] = folder

        folder = cleaned["folder"]
        fn = (cleaned.get("filename") or "").strip()

        if upload:
            base = fn or sanitize_upload_filename(upload.name)
            cleaned["filename"] = unique_filename_for_folder(folder, base)
        elif self.instance.pk:
            cleaned["filename"] = fn or self.instance.filename
        elif fn:
            cleaned["filename"] = unique_filename_for_folder(folder, fn)

        if not cleaned.get("filename"):
            raise forms.ValidationError(
                {"filename": "Enter a filename or upload a file so the name can be set."}
            )

        return cleaned
