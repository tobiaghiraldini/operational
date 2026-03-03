from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Deadline


@admin.register(Deadline)
class DeadlineAdmin(ModelAdmin):
    list_display = ("title", "deadline_type", "due_date", "status", "amount")
    list_filter = ("deadline_type", "status")
    search_fields = ("title",)
    date_hierarchy = "due_date"
