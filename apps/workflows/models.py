from __future__ import annotations

import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.workflows.services.default_definition import default_workflow_definition
from apps.workflows.services.workflow_categories import CATEGORY_CHOICES


class Workflow(models.Model):
    """Tenant-scoped workflow graph (React Flow document, schemaVersion 2)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, null=True, blank=True, unique=True)
    category = models.CharField(
        max_length=32,
        choices=CATEGORY_CHOICES,
        default="general",
        db_index=True,
    )
    description = models.TextField(blank=True)
    definition = models.JSONField(default=default_workflow_definition)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workflows_workflow"
        ordering = ["-updated_at"]
        verbose_name = "Workflow"
        verbose_name_plural = "Workflows"
        # Explicit default so auth always exposes add/change/delete/view (never ``()``).
        default_permissions = ("add", "change", "delete", "view")

    def __str__(self) -> str:
        return self.name


class WorkflowNodeLink(models.Model):
    """Attach an arbitrary tenant object to a React Flow node id within a workflow."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="node_links",
    )
    node_id = models.CharField(max_length=128, db_index=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=64)
    content_object = GenericForeignKey("content_type", "object_id")
    role = models.CharField(max_length=64, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workflows_workflownodelink"
        ordering = ["-created_at"]
        verbose_name = "Workflow node link"
        verbose_name_plural = "Workflow node links"

    def __str__(self) -> str:
        return f"{self.workflow_id}:{self.node_id}→{self.content_type_id}:{self.object_id}"
