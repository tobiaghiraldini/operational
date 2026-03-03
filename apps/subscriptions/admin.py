from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import SubscriptionTier


@admin.register(SubscriptionTier)
class SubscriptionTierAdmin(ModelAdmin):
    list_display = ("name", "slug", "created_at")
    prepopulated_fields = {"slug": ("name",)}
