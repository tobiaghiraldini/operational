from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import DashboardWidget


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(ModelAdmin):
    list_display = ("user", "widget_type", "position", "created_at")
    list_filter = ("widget_type",)
    raw_id_fields = ("user",)
