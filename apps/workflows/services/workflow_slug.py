"""Generate a unique slug for a workflow from a human-readable name."""

from __future__ import annotations

from django.utils.text import slugify

from apps.workflows.models import Workflow


def unique_workflow_slug(name: str) -> str:
    base = (slugify(name.strip()) or "workflow")[:200]
    slug = base
    n = 2
    while Workflow.objects.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug
