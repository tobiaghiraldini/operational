"""Paths and storage helpers for ``DocumentFile`` (FileField + legacy ``file_path``)."""

from __future__ import annotations

import os
import uuid

from django.conf import settings

from apps.documents.folder_paths import (
    normalize_folder_path_for_storage,
    sanitize_upload_filename,
)


def document_upload_to(instance, filename: str) -> str:
    """
    Store under MEDIA-relative ``DocumentFolder.path``::

        {folder_path}/{uuid}_{safe_filename}
    """
    safe_name = sanitize_upload_filename(filename)
    prefix = uuid.uuid4().hex[:12]
    folder_rel = ""
    fld = getattr(instance, "folder", None)
    if fld is not None and getattr(fld, "path", None):
        folder_rel = normalize_folder_path_for_storage(fld.path)
    if not folder_rel:
        from apps.documents.folder_paths import INVOICES_RECEIVED

        folder_rel = INVOICES_RECEIVED
    return f"{folder_rel}/{prefix}_{safe_name}"


def document_absolute_path(doc) -> str:
    """
    Resolve a local filesystem path for opening the binary.

    Prefer ``FileField``; fall back to legacy ``file_path`` (absolute or MEDIA-relative).
    """
    if doc.file and getattr(doc.file, "name", None):
        try:
            return doc.file.path
        except (NotImplementedError, ValueError):
            pass
        rel = doc.file.name.lstrip("/")
        return os.path.normpath(os.path.join(str(settings.MEDIA_ROOT), rel))

    fp = (doc.file_path or "").strip()
    if not fp:
        return ""
    if os.path.isabs(fp):
        return fp
    return os.path.normpath(os.path.join(str(settings.MEDIA_ROOT), fp))


def legacy_file_path_exists(doc) -> bool:
    p = document_absolute_path(doc)
    return bool(p and os.path.isfile(p))
