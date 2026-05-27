from django.urls import include, path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardOverviewView.as_view(), name="overview"),
    path("usage/", views.DashboardUsageView.as_view(), name="usage"),
    path(
        "workflows/api/",
        include(("apps.workflows.urls_api", "workflows_api")),
    ),
    path("workflows/", include(("apps.workflows.urls_dashboard", "workflows"))),
]
