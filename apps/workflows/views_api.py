from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.tenant import TenantSafeQuerysetMixin
from apps.workflows.models import Workflow
from apps.workflows.services.definition_validate import (
    DefinitionValidationError,
    normalize_definition,
)
from apps.workflows.services.react_flow_definition import sanitize_react_flow_definition


class WorkflowDefinitionAPIView(TenantSafeQuerysetMixin, APIView):
    """GET/PUT workflow graph JSON (session auth)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        workflow = get_object_or_404(Workflow.objects.all(), pk=pk)
        return Response(workflow.definition, status=status.HTTP_200_OK)

    def put(self, request, pk):
        workflow = get_object_or_404(Workflow.objects.all(), pk=pk)
        body = request.data
        if not isinstance(body, dict):
            return Response(
                {"detail": "JSON object required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            normalized = normalize_definition(
                sanitize_react_flow_definition(dict(body)),
                workflow_category=workflow.category,
            )
        except DefinitionValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        workflow.definition = normalized
        workflow.save(update_fields=["definition", "updated_at"])
        return Response(workflow.definition, status=status.HTTP_200_OK)
