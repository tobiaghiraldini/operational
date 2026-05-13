from django.db import models
from apps.core.models import BaseModel


class Vendor(BaseModel):
    """
    Vendor/Supplier information model.
    """
    name = models.CharField(max_length=255, help_text="Vendor company name")
    vat_id = models.CharField(max_length=50, blank=True, help_text="VAT identification number")
    address = models.TextField(blank=True, help_text="Complete vendor address")
    country_code = models.CharField(max_length=2, default='IT', help_text="ISO country code")
    email = models.EmailField(blank=True, help_text="Vendor contact email")
    phone = models.CharField(max_length=50, blank=True, help_text="Vendor contact phone")
    is_active = models.BooleanField(default=True, help_text="Whether vendor is active")
    
    class Meta:
        ordering = ['name']
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"
    
    def __str__(self):
        return self.name


class PaymentMethod(BaseModel):
    """
    Payment method definitions for invoices.
    """
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('f24', 'F24'),
        ('paypal', 'PayPal'),
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('other', 'Other'),
    ]
    
    code = models.CharField(max_length=20, unique=True, choices=PAYMENT_METHOD_CHOICES)
    name = models.CharField(max_length=100, help_text="Display name for payment method")
    description = models.TextField(blank=True, help_text="Additional description")
    is_active = models.BooleanField(default=True, help_text="Whether payment method is active")
    is_default = models.BooleanField(
        default=False,
        help_text="Preferred method when creating transactions from invoices without explicit choice.",
    )
    defer_bank_transaction = models.BooleanField(
        default=False,
        help_text="When true, automatic invoice payment posting skips creating a bank transaction until the statement line is booked (e.g. credit card batch settlement).",
    )

    class Meta:
        ordering = ['name']
        verbose_name = "Payment Method"
        verbose_name_plural = "Payment Methods"
    
    def save(self, *args, **kwargs):
        if self.is_default:
            PaymentMethod.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name