"""Expand a ZIP of PDFs into `DocumentFile` rows and queue invoice extraction."""

from __future__ import annotations

import hashlib
import os
import tempfile
import uuid
import zipfile
from typing import Any

from django.conf import settings
from django.core.files.base import ContentFile

from apps.documents.folder_paths import INVOICES_BULK, get_or_create_document_folder
from apps.documents.models import DocumentFile, DocumentFolder
from apps.documents.storage import document_absolute_path
from apps.invoices.tasks import process_single_invoice


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_member_basename(name: str) -> str | None:
    base = os.path.basename(name.replace("\\", "/"))
    if not base or base.startswith(".") or ".." in base:
        return None
    if not base.lower().endswith(".pdf"):
        return None
    return base


def _unique_filename_in_folder(
    folder: DocumentFolder, preferred: str, used: set[str]
) -> str:
    name = preferred
    i = 0
    while name in used or DocumentFile.objects.filter(folder=folder, filename=name).exists():
        i += 1
        stem, sep, ext = preferred.rpartition(".")
        name = f"{stem}_{i}.{ext}" if sep else f"{preferred}_{i}"
    used.add(name)
    return name


def _zip_path_from_upload(zip_file) -> tuple[str, int]:
    """Write upload to a temp file using chunks; return path and byte size."""
    max_zip = getattr(settings, "INVOICE_ZIP_MAX_BYTES", 50 * 1024 * 1024)
    reported = getattr(zip_file, "size", None)
    if reported is not None and reported > max_zip:
        raise ValueError(f"ZIP exceeds limit ({max_zip} bytes).")

    total = 0
    fd, tmp_path = tempfile.mkstemp(suffix=".zip")
    try:
        with os.fdopen(fd, "wb") as out:
            if hasattr(zip_file, "chunks"):
                for chunk in zip_file.chunks():
                    total += len(chunk)
                    if total > max_zip:
                        raise ValueError(f"ZIP exceeds limit ({max_zip} bytes).")
                    out.write(chunk)
            else:
                body = zip_file.read()
                total = len(body)
                if total > max_zip:
                    raise ValueError(f"ZIP exceeds limit ({max_zip} bytes).")
                out.write(body)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return tmp_path, total


def ingest_zip_invoice_pdfs(
    zip_file,
    *,
    folder: DocumentFolder | None = None,
    user_id: int | None = None,
    schema_name: str | None = None,
) -> dict[str, Any]:
    """
    Read PDF members from a ZIP, create ``DocumentFile`` rows with ``FileField`` storage,
    queue Celery invoice extraction for each new PDF.
    """
    max_files = getattr(settings, "INVOICE_ZIP_MAX_FILES", 200)

    tmp_path: str | None = None
    try:
        try:
            tmp_path, _size = _zip_path_from_upload(zip_file)
        except ValueError as exc:
            return {"success": False, "error": str(exc)}

        batch_id = str(uuid.uuid4())

        if folder is None:
            folder, _ = get_or_create_document_folder(
                INVOICES_BULK,
                name="Invoice bulk uploads",
                description="ZIP bulk uploads for daybook / invoice processing.",
            )

        used_names: set[str] = set()
        queued: list[dict[str, Any]] = []
        errors: list[str] = []

        try:
            with zipfile.ZipFile(tmp_path, "r") as zf:
                members = [m for m in zf.namelist() if not m.endswith("/")]
                if len(members) > max_files:
                    return {
                        "success": False,
                        "error": f"Too many ZIP entries (>{max_files}).",
                    }

                for member in members:
                    safe = _safe_member_basename(member)
                    if not safe:
                        continue
                    try:
                        data = zf.read(member)
                    except zipfile.BadZipFile as exc:
                        errors.append(f"{member}: {exc}")
                        continue
                    if not data.startswith(b"%PDF"):
                        errors.append(f"{member}: not a PDF")
                        continue

                    digest = _sha256_bytes(data)
                    dup = DocumentFile.objects.filter(file_hash=digest).first()
                    if dup:
                        queued.append(
                            {
                                "member": member,
                                "filename": safe,
                                "skipped": True,
                                "reason": "duplicate_hash",
                                "document_file_id": dup.pk,
                            }
                        )
                        continue

                    db_filename = _unique_filename_in_folder(folder, safe, used_names)
                    storage_name = f"{digest[:12]}_{db_filename}"

                    doc = DocumentFile(
                        folder=folder,
                        filename=db_filename,
                        file_path="",
                        file_size=len(data),
                        file_hash=digest,
                        file_type="pdf",
                        status="pending",
                    )
                    doc.file.save(storage_name, ContentFile(data), save=False)
                    doc.recompute_file_metadata()
                    doc.save()

                    abs_path = document_absolute_path(doc)
                    async_result = process_single_invoice.delay(
                        abs_path,
                        safe,
                        user_id=user_id,
                        document_file_id=doc.pk,
                        schema_name=schema_name,
                    )
                    queued.append(
                        {
                            "member": member,
                            "filename": db_filename,
                            "document_file_id": doc.pk,
                            "task_id": async_result.id,
                        }
                    )
        except zipfile.BadZipFile:
            return {"success": False, "error": "Invalid or corrupted ZIP file."}

        return {
            "success": True,
            "batch_id": batch_id,
            "queued": sum(1 for x in queued if not x.get("skipped")),
            "items": queued,
            "errors": errors,
        }
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
