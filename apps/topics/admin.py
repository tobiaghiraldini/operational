from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Topic


@admin.register(Topic)
class TopicAdmin(ModelAdmin):
    list_display = ("name", "slug", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "description")
