"""Read ``django_celery_results.models.TaskResult`` (stored in the public schema)."""

from __future__ import annotations

import json
from typing import Any

from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context


def fetch_task_result(task_id: str):
    """
    Return ``TaskResult`` for ``task_id``, or ``None`` if missing.

    Rows for ``django_celery_results`` live in the **public** schema (SHARED_APPS).
    This is not gated by tenant ``UserTenantPermissions`` or per-model Django admin
    permissions — those apply to admin views, not this ORM lookup.

    Lookup order:

    1. ORM inside ``schema_context(public)`` (normal case).
    2. Raw SQL against ``<public>.<TaskResult._meta.db_table>`` then ORM by pk, still
       in public context — avoids odd manager / routing edge cases.
    3. ORM on the current connection after restoring tenant context — covers legacy
       installs where a copy of the results table exists in a tenant schema and the
       worker wrote there first on the search_path.
    """
    if not (task_id or "").strip():
        return None
    from django_celery_results.models import TaskResult

    tid = task_id.strip()
    public_name = get_public_schema_name()

    with schema_context(public_name):
        hit = TaskResult.objects.filter(task_id=tid).first()
        if hit is not None:
            return hit
        schema_q = connection.ops.quote_name(public_name)
        tbl_q = connection.ops.quote_name(TaskResult._meta.db_table)
        sql = f"SELECT id FROM {schema_q}.{tbl_q} WHERE task_id = %s LIMIT 1"
        with connection.cursor() as cursor:
            cursor.execute(sql, [tid])
            row = cursor.fetchone()
        if row:
            return TaskResult.objects.filter(pk=row[0]).first()

    if connection.schema_name != public_name:
        return TaskResult.objects.filter(task_id=tid).first()
    return None


def task_result_progress_summary(task_result) -> dict[str, Any]:
    """
    Build a small dict for admin display: status, percent (if any), stage, dates.
    """
    if task_result is None:
        return {"found": False}
    meta: dict[str, Any] = {}
    if task_result.meta:
        try:
            meta = json.loads(task_result.meta)
        except (json.JSONDecodeError, TypeError):
            meta = {}
    percent = None
    if isinstance(meta, dict):
        if "percent" in meta:
            try:
                percent = int(meta["percent"])
            except (TypeError, ValueError):
                percent = None
        elif isinstance(meta.get("current"), (int, float)) and isinstance(
            meta.get("total"), (int, float)
        ):
            t = float(meta["total"])
            if t > 0:
                percent = int(100.0 * float(meta["current"]) / t)
    stage = meta.get("stage") if isinstance(meta, dict) else None
    return {
        "found": True,
        "status": task_result.status,
        "percent": percent,
        "stage": stage,
        "date_started": task_result.date_started,
        "date_done": task_result.date_done,
        "worker": task_result.worker,
    }
