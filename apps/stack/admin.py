from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.stack.models import Technology, TechnologyUsage


@admin.register(Technology)
class TechnologyAdmin(ModelAdmin):
    list_display = ("name", "kind", "version_label")
    list_filter = ("kind",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(TechnologyUsage)
class TechnologyUsageAdmin(ModelAdmin):
    list_display = ("technology", "content_type", "object_id", "role")
    list_filter = ("technology",)
