from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Deadline


@admin.register(Deadline)
class DeadlineAdmin(ModelAdmin):
    list_display = ("title", "project", "deadline_type", "due_date", "status", "amount")
    list_filter = ("deadline_type", "status", "project")
    search_fields = ("title",)
    date_hierarchy = "due_date"
