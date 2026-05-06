from django.db import models
from apps.core.models import BaseModel
from apps.tenants.models import Tenant as Client
from apps.tenants.models import Domain


class Customer(BaseModel):
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    vat_id = models.CharField(max_length=64, blank=True)
    tax_code = models.CharField(max_length=64, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=128, blank=True)
    postal_code = models.CharField(max_length=16, blank=True)
    country_code = models.CharField(max_length=2, default="IT")
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "vat_id"], name="customers_customer_name_vat_uniq"),
        ]

    def __str__(self):
        return self.name
