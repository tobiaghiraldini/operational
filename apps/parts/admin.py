from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Part


@admin.register(Part)
class PartAdmin(ModelAdmin):
    list_display = ("name", "part_type", "content_type", "object_id", "created_at")
    list_filter = ("part_type", "content_type")
