from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Article


@admin.register(Article)
class ArticleAdmin(ModelAdmin):
    list_display = ("title", "slug", "updated_at")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "body")
