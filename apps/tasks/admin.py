from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Task


@admin.register(Task)
class TaskAdmin(ModelAdmin):
    list_display = ("title", "status", "priority", "due_date", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "description")
