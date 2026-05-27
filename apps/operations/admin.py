from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.operations.models import OperationalSnapshot


@admin.register(OperationalSnapshot)
class OperationalSnapshotAdmin(ModelAdmin):
    list_display = ("project", "overall_status", "source", "recorded_at")
    list_filter = ("overall_status", "source")
