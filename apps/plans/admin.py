from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Plan


@admin.register(Plan)
class PlanAdmin(ModelAdmin):
    list_display = ("name", "start_date", "end_date", "created_at")
    list_filter = ("start_date", "end_date")
    search_fields = ("name", "description")
