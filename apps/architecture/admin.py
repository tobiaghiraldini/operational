from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.architecture.models import (
    ArchitectureComponent,
    ArchitectureConnection,
    ArchitectureProfile,
)


class ArchitectureComponentInline(TabularInline):
    model = ArchitectureComponent
    extra = 0
    fields = ("name", "component_type", "vendor", "engine", "status")


@admin.register(ArchitectureProfile)
class ArchitectureProfileAdmin(ModelAdmin):
    list_display = ("name", "project", "environment", "is_primary")
    list_filter = ("environment", "is_primary")
    search_fields = ("name", "project__name")
    inlines = [ArchitectureComponentInline]


@admin.register(ArchitectureComponent)
class ArchitectureComponentAdmin(ModelAdmin):
    list_display = ("name", "profile", "component_type", "vendor", "status")
    list_filter = ("component_type", "status")
    search_fields = ("name", "vendor", "engine")


@admin.register(ArchitectureConnection)
class ArchitectureConnectionAdmin(ModelAdmin):
    list_display = ("source", "connection_type", "target")
    list_filter = ("connection_type",)
