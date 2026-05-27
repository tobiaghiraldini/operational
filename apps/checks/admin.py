from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.checks.models import PlannedCheck


@admin.register(PlannedCheck)
class PlannedCheckAdmin(ModelAdmin):
    list_display = ("name", "check_type", "project", "system", "next_run_at")
    list_filter = ("check_type",)
