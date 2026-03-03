from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Milestone


@admin.register(Milestone)
class MilestoneAdmin(ModelAdmin):
    list_display = ("name", "plan", "target_date", "status", "order")
    list_filter = ("status", "plan")
    search_fields = ("name", "description")
    raw_id_fields = ("plan",)
