from django.urls import path

from apps.workflows import views_api, views_workflow_links

app_name = "workflows_api"

urlpatterns = [
    path(
        "<uuid:pk>/definition/",
        views_api.WorkflowDefinitionAPIView.as_view(),
        name="definition",
    ),
    path(
        "<uuid:pk>/links/",
        views_workflow_links.WorkflowNodeLinkListCreateView.as_view(),
        name="node_links",
    ),
    path(
        "<uuid:pk>/links/<uuid:link_id>/",
        views_workflow_links.WorkflowNodeLinkDetailView.as_view(),
        name="node_link_detail",
    ),
]
