from django.contrib import admin
from unfold.admin import ModelAdmin
from django_tenants.admin import TenantAdminMixin

from apps.customers.models import Client, Domain


@admin.register(Client)
class ClientAdmin(TenantAdminMixin, ModelAdmin):
    list_display = ("name", "paid_until")


@admin.register(Domain)
class DomainAdmin(TenantAdminMixin, ModelAdmin):
    list_display = ("domain", "tenant")