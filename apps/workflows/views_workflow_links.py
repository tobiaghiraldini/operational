from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.tenant import TenantSafeQuerysetMixin
from apps.workflows.models import Workflow, WorkflowNodeLink


def _node_ids_from_definition(definition: dict) -> set[str]:
    nodes = definition.get("nodes")
    if not isinstance(nodes, list):
        return set()
    out: set[str] = set()
    for n in nodes:
        if isinstance(n, dict) and isinstance(n.get("id"), str):
            out.add(str(n["id"]).strip())
    return out


def _serialize_link(link: WorkflowNodeLink) -> dict:
    ct = link.content_type
    return {
        "id": str(link.pk),
        "node_id": link.node_id,
        "app_label": ct.app_label,
        "model": ct.model,
        "object_id": str(link.object_id),
        "role": link.role,
        "notes": link.notes,
    }


class WorkflowNodeLinkListCreateView(TenantSafeQuerysetMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        workflow = get_object_or_404(Workflow.objects.all(), pk=pk)
        qs = WorkflowNodeLink.objects.filter(workflow=workflow).select_related("content_type")
        return Response([_serialize_link(l) for l in qs])

    def post(self, request, pk):
        workflow = get_object_or_404(Workflow.objects.all(), pk=pk)
        body = request.data
        if not isinstance(body, dict):
            return Response({"detail": "JSON object required"}, status=status.HTTP_400_BAD_REQUEST)
        node_id = (body.get("node_id") or "").strip()
        app_label = (body.get("app_label") or "").strip()
        model = (body.get("model") or "").strip().lower()
        object_id = str(body.get("object_id") or "").strip()
        role = (body.get("role") or "").strip()[:64]
        notes = (body.get("notes") or "").strip()
        if not node_id or not app_label or not model or not object_id:
            return Response(
                {"detail": "node_id, app_label, model, and object_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        allowed = _node_ids_from_definition(workflow.definition if isinstance(workflow.definition, dict) else {})
        if node_id not in allowed:
            return Response({"detail": "node_id is not part of this workflow graph"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            ct = ContentType.objects.get(app_label=app_label, model=model)
        except ContentType.DoesNotExist:
            return Response({"detail": "Unknown content type"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            ct.get_object_for_this_type(pk=object_id)
        except (ObjectDoesNotExist, ValueError, TypeError):
            return Response({"detail": "Target object not found"}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            link = WorkflowNodeLink.objects.create(
                workflow=workflow,
                node_id=node_id,
                content_type=ct,
                object_id=object_id,
                role=role,
                notes=notes,
            )
        return Response(_serialize_link(link), status=status.HTTP_201_CREATED)


class WorkflowNodeLinkDetailView(TenantSafeQuerysetMixin, APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, link_id):
        workflow = get_object_or_404(Workflow.objects.all(), pk=pk)
        link = get_object_or_404(WorkflowNodeLink.objects.filter(workflow=workflow), pk=link_id)
        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
