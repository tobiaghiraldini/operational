from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.products.models import Product, ProductLicense, ProjectProduct


class ProductLicenseInline(TabularInline):
    model = ProductLicense
    extra = 0


class ProjectProductInline(TabularInline):
    model = ProjectProduct
    extra = 0
    autocomplete_fields = ("project",)


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ("name", "vendor", "product_kind", "updated_at")
    list_filter = ("product_kind",)
    search_fields = ("name", "vendor", "description")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("topics",)
    inlines = [ProductLicenseInline, ProjectProductInline]


@admin.register(ProductLicense)
class ProductLicenseAdmin(ModelAdmin):
    list_display = ("product", "license_type", "status", "ends_at")
    list_filter = ("license_type", "status")
