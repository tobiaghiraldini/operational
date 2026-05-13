"""MEDIA-relative logical paths for ``DocumentFolder`` and upload routing."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.documents.models import DocumentFolder

INVOICES_RECEIVED = "invoices/received"
INVOICES_EMITTED = "invoices/emitted"
INVOICES_BULK = "invoices/bulk"

# Admin / form: maps to ``DocumentFolder.path`` via ``folder_for_storage_kind``.
STORAGE_KIND_RECEIVED = "received"
STORAGE_KIND_EMITTED = "emitted"
STORAGE_KIND_BULK = "bulk"

STORAGE_KIND_CHOICES = (
    (STORAGE_KIND_RECEIVED, "Received invoices"),
    (STORAGE_KIND_EMITTED, "Emitted invoices"),
    (STORAGE_KIND_BULK, "Bulk (ZIP batch)"),
)


def sanitize_upload_filename(name: str, max_length: int = 200) -> str:
    """
    Safe basename for storage and ``DocumentFile.filename``: strip path segments,
    replace unsafe characters, keep extension when present.
    """
    base = Path(str(name)).name
    if not base or base in (".", ".."):
        return "upload.bin"

    if "." in base:
        stem, ext = base.rsplit(".", 1)
        safe_stem = re.sub(r"[^\w\-.]", "_", stem)
        safe_stem = re.sub(r"_+", "_", safe_stem).strip("._") or "file"
        safe_ext = re.sub(r"[^\w]", "", ext.lower())[:12] or "bin"
        out = f"{safe_stem[:160]}.{safe_ext}"
    else:
        safe_stem = re.sub(r"[^\w\-.]", "_", base)
        safe_stem = re.sub(r"_+", "_", safe_stem).strip("._") or "file"
        out = safe_stem[:max_length]

    return out[:max_length]


def normalize_folder_path_for_storage(folder_path: str) -> str:
    """Strip traversal and normalize slashes to a single MEDIA-relative path."""
    rel = (folder_path or "").strip().replace("\\", "/").strip("/")
    segments: list[str] = []
    for seg in rel.split("/"):
        seg = seg.strip()
        if not seg or seg in (".", "..") or ".." in seg:
            continue
        segments.append(seg)
    return "/".join(segments)


def get_or_create_document_folder(
    path: str,
    *,
    name: str,
    description: str = "",
    auto_process: bool = True,
) -> tuple[DocumentFolder, bool]:
    """Ensure a ``DocumentFolder`` exists for the given MEDIA-relative ``path``."""
    from apps.documents.models import DocumentFolder as DocumentFolderModel


    normalized = normalize_folder_path_for_storage(path)
    if not normalized:
        normalized = INVOICES_RECEIVED
    return DocumentFolderModel.objects.get_or_create(
        path=normalized,
        defaults={
            "name": name,
            "description": description,
            "is_active": True,
            "auto_process": auto_process,
        },
    )


def folder_for_storage_kind(kind: str | None) -> tuple[DocumentFolder, bool]:
    """Resolve admin ``invoice_storage_kind`` to a folder."""
    k = (kind or STORAGE_KIND_RECEIVED).strip().lower()
    if k == STORAGE_KIND_EMITTED:
        return get_or_create_document_folder(
            INVOICES_EMITTED,
            name="Invoices emitted",
            description="Outgoing / emitted invoice PDFs.",
        )
    if k == STORAGE_KIND_BULK:
        return get_or_create_document_folder(
            INVOICES_BULK,
            name="Invoice bulk uploads",
            description="ZIP batches and bulk invoice archives.",
        )
    return get_or_create_document_folder(
        INVOICES_RECEIVED,
        name="Invoices received",
        description="Incoming / received invoice PDFs.",
    )


def get_invoice_folder_for_invoice_type(invoice_type: str | None) -> tuple[DocumentFolder, bool]:
    """Map API / hint ``invoice_type`` (``received`` / ``emitted``) to storage folder."""
    t = (invoice_type or "").strip().lower()
    if t == "emitted":
        return get_or_create_document_folder(
            INVOICES_EMITTED,
            name="Invoices emitted",
            description="Outgoing / emitted invoice PDFs.",
        )
    return get_or_create_document_folder(
        INVOICES_RECEIVED,
        name="Invoices received",
        description="Incoming / received invoice PDFs.",
    )


def unique_filename_for_folder(folder: DocumentFolder, desired: str) -> str:
    """Ensure ``(folder, filename)`` uniqueness for ``DocumentFile``."""
    from apps.documents.models import DocumentFile

    base = sanitize_upload_filename(desired)
    if "." in base:
        stem, ext = base.rsplit(".", 1)
    else:
        stem, ext = base, ""

    name = base
    n = 0
    while DocumentFile.objects.filter(folder=folder, filename=name).exists():
        n += 1
        if ext:
            name = f"{stem}_{n}.{ext}"
        else:
            name = f"{stem}_{n}"
        if len(name) > 255:
            stem = stem[:200]
            name = f"{stem}_{n}.{ext}" if ext else f"{stem}_{n}"
    return name
