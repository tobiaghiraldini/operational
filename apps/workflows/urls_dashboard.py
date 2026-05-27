from django.urls import path

from apps.workflows import views_dashboard

app_name = "workflows"

urlpatterns = [
    path("", views_dashboard.WorkflowListView.as_view(), name="list"),
    path("new/", views_dashboard.WorkflowCreateView.as_view(), name="create"),
    path("<uuid:pk>/edit/", views_dashboard.WorkflowEditorView.as_view(), name="editor"),
]
