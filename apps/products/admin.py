from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Product


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ("name", "slug", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
