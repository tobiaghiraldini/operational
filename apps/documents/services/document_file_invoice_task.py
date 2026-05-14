"""Update ``DocumentFile`` status when invoice extraction runs in Celery."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

if TYPE_CHECKING:
    from apps.documents.models import DocumentFile

logger = logging.getLogger(__name__)


def mark_processing(document_file: DocumentFile | None) -> None:
    if not document_file:
        return
    # Use QuerySet.update to avoid nested savepoints and stale instances.
    # Do NOT call close_old_connections() here: it drops the django-tenants schema
    # set by TenantTask / schema_context, so updates would hit the wrong schema.
    with transaction.atomic():
        type(document_file).objects.filter(pk=document_file.pk).update(
            status="processing",
            error_message="",
            updated_at=timezone.now(),
        )


def mark_processing_with_task_id(document_file_pk: int | None, task_id: str) -> None:
    """
    After ``process_single_invoice.delay(...)``, persist task id and show ``processing``
    immediately (before the worker runs ``mark_processing``).
    """
    if document_file_pk is None or not (task_id or "").strip():
        return
    from apps.documents.models import DocumentFile

    now = timezone.now()
    tid = task_id.strip()
    with transaction.atomic():
        DocumentFile.objects.filter(pk=document_file_pk).update(
            status="processing",
            error_message="",
            processing_task_id=tid,
            updated_at=now,
        )


def mark_success(document_file: DocumentFile | None) -> None:
    if not document_file:
        return
    now = timezone.now()
    with transaction.atomic():
        type(document_file).objects.filter(pk=document_file.pk).update(
            status="processed",
            processed_at=now,
            error_message="",
            updated_at=now,
        )


def mark_failure(document_file: DocumentFile | None, message: str) -> None:
    if not document_file:
        return
    with transaction.atomic():
        type(document_file).objects.filter(pk=document_file.pk).update(
            status="error",
            error_message=(message or "")[:2000],
            updated_at=timezone.now(),
        )


def mark_success_safe(document_file: DocumentFile | None) -> None:
    """Like ``mark_success`` but never raises (invoice row is already committed)."""
    if not document_file:
        return
    try:
        mark_success(document_file)
    except Exception:
        logger.exception(
            "Failed to mark DocumentFile pk=%s as processed after successful extraction",
            getattr(document_file, "pk", None),
        )


def mark_failure_safe(document_file: DocumentFile | None, message: str) -> None:
    """Like ``mark_failure`` but never raises (e.g. connection still broken)."""
    if not document_file:
        return
    try:
        mark_failure(document_file, message)
    except Exception:
        logger.exception(
            "Failed to persist DocumentFile pk=%s error state",
            getattr(document_file, "pk", None),
        )
