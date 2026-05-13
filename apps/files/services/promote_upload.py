"""Move a FilePond temporary upload into permanent storage and register a `DocumentFile`."""

from __future__ import annotations

import hashlib
import os
from typing import NamedTuple

from django.conf import settings
from django.core.files import File
from django.db import IntegrityError
from django_drf_filepond.api import store_upload
from django_drf_filepond.models import TemporaryUpload

from apps.documents.folder_paths import (
    get_invoice_folder_for_invoice_type,
    sanitize_upload_filename,
    unique_filename_for_folder,
)
from apps.documents.models import DocumentFile
from apps.documents.storage import document_absolute_path


class PromotedUpload(NamedTuple):
    file_path: str
    document_file: DocumentFile
    original_filename: str


def _stored_absolute_path(stored_upload) -> str:
    if hasattr(stored_upload, "get_absolute_file_path"):
        return stored_upload.get_absolute_file_path()
    base = getattr(settings, "DJANGO_DRF_FILEPOND_FILE_STORE_PATH", "") or ""
    return os.path.join(base, stored_upload.file.name)


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(4096), b""):
                digest.update(chunk)
    except OSError:
        return ""
    return digest.hexdigest()


def finalize_invoice_upload(
    upload_id: str,
    *,
    invoice_type: str | None = None,
) -> PromotedUpload:
    """
    Store the FilePond temp file, create ``DocumentFile`` in the folder for
    ``invoice_type`` (``received`` / ``emitted``; default received).
    """
    temp_upload = TemporaryUpload.objects.get(upload_id=upload_id)
    stored = store_upload(
        upload_id, destination_file_path=f"invoices/{temp_upload.upload_name}"
    )
    if not stored:
        raise RuntimeError("FilePond store_upload returned no stored upload")

    src_abs = _stored_absolute_path(stored)
    file_size = os.path.getsize(src_abs) if os.path.isfile(src_abs) else 0
    max_bytes = getattr(settings, "INVOICE_MAX_UPLOAD_BYTES", 25 * 1024 * 1024)
    if file_size > max_bytes:
        try:
            os.remove(src_abs)
        except OSError:
            pass
        raise RuntimeError(f"File exceeds maximum upload size ({max_bytes} bytes).")

    file_hash = _sha256_file(src_abs) if file_size else ""

    if file_hash:
        duplicate = DocumentFile.objects.filter(file_hash=file_hash).first()
        if duplicate:
            return PromotedUpload(
                file_path=document_absolute_path(duplicate),
                document_file=duplicate,
                original_filename=os.path.basename(duplicate.filename),
            )

    raw_name = os.path.basename(temp_upload.upload_name) or "upload.pdf"

    folder, _ = get_invoice_folder_for_invoice_type(invoice_type)
    basename = unique_filename_for_folder(folder, sanitize_upload_filename(raw_name))
    ext = basename.rsplit(".", 1)[-1].lower() if "." in basename else "pdf"

    def _build_and_save(name: str) -> DocumentFile:
        doc = DocumentFile(
            folder=folder,
            filename=name,
            file_path="",
            file_size=0,
            file_hash="",
            file_type=ext,
            status="pending",
        )
        with open(src_abs, "rb") as fh:
            doc.file.save(name, File(fh), save=False)
        doc.recompute_file_metadata()
        doc.save()
        return doc

    try:
        document = _build_and_save(basename)
    except IntegrityError:
        basename = f"{temp_upload.upload_id[:10]}_{basename}"
        document = _build_and_save(basename)

    return PromotedUpload(
        file_path=document_absolute_path(document),
        document_file=document,
        original_filename=basename,
    )
