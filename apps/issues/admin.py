from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.issues.models import Issue


@admin.register(Issue)
class IssueAdmin(ModelAdmin):
    list_display = ("title", "project", "severity", "status", "reported_at")
    list_filter = ("severity", "status")
    search_fields = ("title", "description")
