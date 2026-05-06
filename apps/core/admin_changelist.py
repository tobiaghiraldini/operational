"""Shared changelist enhancements for admin."""


class ChangelistMetricsMixin:
    """Inject metric cards rendered above changelist tables."""

    list_before_template = "admin/includes/pre_changelist_metrics.html"

    def get_changelist_metrics(self, request, queryset):
        """Return a list of metric cards for changelist pages."""
        return []

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        queryset = self.get_queryset(request)
        extra_context["changelist_metrics"] = self.get_changelist_metrics(
            request, queryset
        )
        return super().changelist_view(request, extra_context=extra_context)
