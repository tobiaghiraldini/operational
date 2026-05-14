from __future__ import annotations

from django.views.generic import TemplateView


class DashboardOverviewView(TemplateView):
    template_name = "dashboard/overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = "overview"
        cells = []
        for week in range(12):
            for day in range(7):
                cells.append((week * 3 + day * 5) % 5)
        context["heatmap_cells"] = cells
        return context


class DashboardUsageView(TemplateView):
    template_name = "dashboard/usage.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = "usage"
        context["usage_rows"] = [
            {"when": "May 13 at 02:14 PM", "kind": "Included", "model": "auto", "tokens": "1.0M", "cost": "Included"},
            {"when": "May 13 at 01:02 PM", "kind": "Included", "model": "gpt-5", "tokens": "420K", "cost": "Included"},
            {"when": "May 12 at 06:30 PM", "kind": "Included", "model": "auto", "tokens": "890K", "cost": "Included"},
        ]
        return context
