from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import System


@admin.register(System)
class SystemAdmin(ModelAdmin):
    list_display = ("name", "system_type", "environment", "created_at")
    list_filter = ("system_type", "environment")
    search_fields = ("name", "description")
