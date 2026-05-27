from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Task


@admin.register(Task)
class TaskAdmin(ModelAdmin):
    list_display = ("title", "project", "status", "priority", "due_date", "assignee")
    list_filter = ("status", "project")
    search_fields = ("title", "description")
