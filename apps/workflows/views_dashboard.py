from __future__ import annotations

from django.http import HttpResponseRedirect
from django.middleware.csrf import get_token
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView

from apps.workflows.forms.workflow_create import WorkflowCreateForm
from apps.workflows.models import Workflow
from apps.workflows.services.default_definition import default_workflow_definition
from apps.workflows.services.node_card_registry import node_types_for_category
from apps.workflows.services.workflow_categories import (
    CATEGORY_CHOICES,
    CATEGORY_LABELS,
    primary_node_type_for_category,
)
from apps.workflows.services.workflow_slug import unique_workflow_slug


class WorkflowListView(ListView):
    model = Workflow
    template_name = "workflows/dashboard_list.html"
    context_object_name = "workflows"

    def get_queryset(self):
        qs = super().get_queryset()
        cat = (self.request.GET.get("category") or "").strip()
        valid = {c for c, _ in CATEGORY_CHOICES}
        if cat in valid:
            qs = qs.filter(category=cat)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = "workflows"
        context["category_choices"] = CATEGORY_CHOICES
        cat = (self.request.GET.get("category") or "").strip()
        context["filter_category"] = cat if cat in dict(CATEGORY_CHOICES) else ""
        return context


class WorkflowCreateView(CreateView):
    model = Workflow
    form_class = WorkflowCreateForm
    template_name = "workflows/dashboard_create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = "workflows"
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.slug = unique_workflow_slug(self.object.name)
        self.object.definition = default_workflow_definition(category=self.object.category)
        self.object.save()
        return HttpResponseRedirect(
            reverse("dashboard:workflows:editor", kwargs={"pk": self.object.pk})
        )


class WorkflowEditorView(DetailView):
    model = Workflow
    template_name = "workflows/dashboard_editor.html"
    context_object_name = "workflow"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = "workflows"
        wf: Workflow = self.object
        context["definition"] = wf.definition
        context["definition_api_url"] = self.request.build_absolute_uri(
            reverse("dashboard:workflows_api:definition", kwargs={"pk": wf.pk})
        )
        context["links_api_url"] = self.request.build_absolute_uri(
            reverse("dashboard:workflows_api:node_links", kwargs={"pk": wf.pk})
        )
        context["workflow_node_types"] = sorted(node_types_for_category(wf.category))
        context["workflow_primary_node_type"] = primary_node_type_for_category(wf.category)
        context["workflow_category_label"] = CATEGORY_LABELS.get(wf.category, wf.category)
        context["workflow_category"] = wf.category
        context["editor_csrf_token"] = get_token(self.request)
        return context
