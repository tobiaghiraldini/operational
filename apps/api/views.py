from django.http import JsonResponse


def api_root(request):
    """High-level API root: list available resource links (tenant-aware when on tenant)."""
    data = {
        "name": "Operational API",
        "version": "1",
        "links": {
            "plans": "/api/plans/",
            "milestones": "/api/milestones/",
            "products": "/api/products/",
            "systems": "/api/systems/",
            "parts": "/api/parts/",
            "topics": "/api/topics/",
            "knowledge": "/api/knowledge/",
            "tasks": "/api/tasks/",
            "deadlines": "/api/deadlines/",
            "money": "/api/money/",
            "accounting": "/api/accounting/",
            "dashboard": "/api/dashboard/",
        },
    }
    if hasattr(request, "tenant") and request.tenant:
        data["tenant"] = str(request.tenant.schema_name)
    return JsonResponse(data)
