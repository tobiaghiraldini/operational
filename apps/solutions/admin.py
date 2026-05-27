from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.solutions.models import Solution


@admin.register(Solution)
class SolutionAdmin(ModelAdmin):
    list_display = ("title", "project", "status", "updated_at")
    list_filter = ("status",)
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("systems", "topics")
