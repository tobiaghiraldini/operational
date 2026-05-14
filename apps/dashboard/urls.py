from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardOverviewView.as_view(), name="overview"),
    path("usage/", views.DashboardUsageView.as_view(), name="usage"),
]
