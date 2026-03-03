from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import MoneyCategory, Transaction


@admin.register(MoneyCategory)
class MoneyCategoryAdmin(ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_display = ("amount", "kind", "date", "category", "counterparty")
    list_filter = ("kind", "category", "date")
    search_fields = ("counterparty", "note")
    raw_id_fields = ("category",)
    date_hierarchy = "date"
