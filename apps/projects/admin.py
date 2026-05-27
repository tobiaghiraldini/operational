from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.products.models import ProjectProduct
from apps.projects.models import Project


class ProjectProductInline(admin.TabularInline):
    model = ProjectProduct
    extra = 0
    autocomplete_fields = ("product",)


@admin.register(Project)
class ProjectAdmin(ModelAdmin):
    list_display = ("name", "slug", "status", "owner", "updated_at")
    list_filter = ("status",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("topics", "plans", "systems", "milestones")
    inlines = [ProjectProductInline]
