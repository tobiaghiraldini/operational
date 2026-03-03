from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import JournalEntry, JournalEntryLine


class JournalEntryLineInline(admin.TabularInline):
    model = JournalEntryLine
    extra = 1


@admin.register(JournalEntry)
class JournalEntryAdmin(ModelAdmin):
    list_display = ("date", "reference", "created_at")
    list_filter = ("date",)
    search_fields = ("reference", "note")
    inlines = [JournalEntryLineInline]
    date_hierarchy = "date"
