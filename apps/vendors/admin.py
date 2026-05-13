from django.contrib import admin
from .models import Vendor, PaymentMethod
from unfold.admin import ModelAdmin
from apps.core.admin_mixins import TenantSchemaOnlyAdminMixin


@admin.register(Vendor)
class VendorAdmin(TenantSchemaOnlyAdminMixin, ModelAdmin):
    list_display = ['name', 'vat_id', 'country_code', 'is_active', 'created_at']
    list_filter = ['is_active', 'country_code', 'created_at']
    search_fields = ['name', 'vat_id', 'email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'vat_id', 'country_code', 'is_active')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'address')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PaymentMethod)
class PaymentMethodAdmin(TenantSchemaOnlyAdminMixin, ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'is_default', 'created_at']
    list_filter = ['is_active', 'is_default', 'code']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'description', 'is_active', 'is_default')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )