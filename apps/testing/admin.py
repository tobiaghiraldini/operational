from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.testing.models import TestRun, TestScenario


class TestRunInline(TabularInline):
    model = TestRun
    extra = 0
    readonly_fields = ("run_at",)


@admin.register(TestScenario)
class TestScenarioAdmin(ModelAdmin):
    list_display = ("title", "project", "kind", "is_active")
    list_filter = ("kind", "is_active")
    inlines = [TestRunInline]


@admin.register(TestRun)
class TestRunAdmin(ModelAdmin):
    list_display = ("scenario", "outcome", "run_at", "run_by")
    list_filter = ("outcome",)
