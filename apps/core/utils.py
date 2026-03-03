"""
Shared utilities, validators, and helpers used across Operational apps.
Domain-agnostic logic lives here; serializers stay in API app.
"""


def get_tenant_from_request(request):
    """Return the current tenant (Client) for the request, if any."""
    if hasattr(request, "tenant") and request.tenant is not None:
        return request.tenant
    return None
