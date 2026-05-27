from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import System


@admin.register(System)
class SystemAdmin(ModelAdmin):
    list_display = ("name", "slug", "system_type", "environment", "owner")
    list_filter = ("system_type", "environment")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("topics", "depends_on")
