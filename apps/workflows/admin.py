from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.workflows.models import Workflow, WorkflowNodeLink


@admin.register(Workflow)
class WorkflowAdmin(ModelAdmin):
    list_display = ("name", "category", "slug", "updated_at")
    list_filter = ("category",)
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("id", "created_at", "updated_at", "definition_preview")

    fieldsets = (
        (None, {"fields": ("name", "slug", "category", "description")}),
        (
            "Definition",
            {
                "fields": ("definition_preview",),
                "description": "Edit the graph on the tenant dashboard under Workflows.",
            },
        ),
        ("Meta", {"fields": ("id", "created_at", "updated_at")}),
    )

    @admin.display(description="Definition (read-only)")
    def definition_preview(self, obj: Workflow) -> str:
        if not getattr(obj, "pk", None):
            return "—"
        import json

        try:
            text = json.dumps(obj.definition, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            return "(invalid JSON)"
        if len(text) > 4000:
            return text[:4000] + "\n…"
        return text

    def save_model(self, request, obj, form, change):
        if isinstance(obj.definition, dict):
            d = dict(obj.definition)
            meta = dict(d.get("meta") or {})
            meta["category"] = obj.category
            d["meta"] = meta
            obj.definition = d
        super().save_model(request, obj, form, change)


@admin.register(WorkflowNodeLink)
class WorkflowNodeLinkAdmin(ModelAdmin):
    list_display = ("workflow", "node_id", "content_type", "object_id", "role", "created_at")
    list_filter = ("content_type",)
    search_fields = ("node_id", "role", "notes")
    readonly_fields = ("id", "created_at")
