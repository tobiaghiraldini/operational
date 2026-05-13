from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model
from apps.core.models import BaseModel
from apps.vendors.models import Vendor, PaymentMethod

User = get_user_model()


class Invoice(BaseModel):
    """
    Invoice model storing extracted invoice data.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Extraction'),
        ('extracted', 'Data Extracted'),
        ('review', 'Needs Manual Review'),
        ('completed', 'Processing Completed'),
        ('error', 'Processing Error'),
    ]
    
    INVOICE_TYPE_CHOICES = [
        ('received', 'Received Invoice'),
        ('emitted', 'Emitted Invoice'),
    ]
    
    # Invoice identification
    invoice_number = models.CharField(max_length=100, help_text="Invoice number from document")
    invoice_date = models.DateField(help_text="Date when invoice was issued")
    due_date = models.DateField(help_text="Payment due date")
    payment_date = models.DateField(null=True, blank=True, help_text="Actual payment date")
    
    # Financial information
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(0)],
        help_text="Total invoice amount"
    )
    currency = models.ForeignKey(
        "money.Currency",
        on_delete=models.PROTECT,
        related_name="invoices",
        help_text="Invoice currency (ISO 4217 row in money.Currency).",
    )
    converted_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Amount converted to base currency"
    )
    exchange_rate = models.DecimalField(
        max_digits=8, 
        decimal_places=4, 
        null=True, 
        blank=True,
        help_text="Exchange rate used for conversion"
    )
    
    # VAT information
    vat_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="VAT percentage applied"
    )
    vat_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="VAT amount"
    )
    taxable_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Amount before VAT"
    )
    
    # Relationships
    vendor = models.ForeignKey(
        Vendor, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='invoices',
        help_text="Vendor who issued the invoice"
    )
    customer = models.ForeignKey(
        'customers.Customer', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='invoices',
        help_text="Customer who received the invoice"
    )
    payment_method = models.ForeignKey(
        PaymentMethod, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Payment method used"
    )
    
    # File information
    original_filename = models.CharField(max_length=255, help_text="Original PDF filename", blank=True, null=True)
    file_path = models.CharField(max_length=500, help_text="Path to PDF file", blank=True, null=True)
    file_size = models.IntegerField(default=0, help_text="File size in bytes")
    
    # Processing status
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        help_text="Processing status"
    )
    needs_manual_review = models.BooleanField(
        default=False, 
        help_text="Whether manual review is required"
    )
    extraction_errors = models.TextField(
        blank=True, 
        help_text="Any errors encountered during processing"
    )
    
    # Additional metadata
    notes = models.TextField(blank=True, help_text="Additional notes or comments")
    invoice_type = models.CharField(
        max_length=20,
        choices=INVOICE_TYPE_CHOICES,
        default='received',
        help_text="Type of invoice: received (from vendor) or emitted (to customer)"
    )
    
    # Template reference
    template = models.ForeignKey(
        'InvoiceTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices',
        help_text="Invoice template used for extraction"
    )
    
    # Source document file reference
    document_file = models.ForeignKey(
        'documents.DocumentFile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices',
        help_text="Source document file this invoice was created from (if applicable)"
    )

    DOCUMENT_KIND_CHOICES = [
        ("invoice", "Invoice"),
        ("credit_note", "Credit note"),
        ("proforma", "Pro forma"),
        ("other", "Other"),
    ]

    classification_hints = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optional upload-time hints (invoice_type, vendor_id, currency, notes, …) for extraction.",
    )
    document_kind = models.CharField(
        max_length=20,
        choices=DOCUMENT_KIND_CHOICES,
        default="invoice",
        help_text="Kind of source document",
    )
    supplier_vat_id = models.CharField(max_length=64, blank=True)
    customer_vat_id = models.CharField(max_length=64, blank=True)
    purchase_order_reference = models.CharField(max_length=120, blank=True)
    payment_reference = models.CharField(max_length=120, blank=True)
    iban = models.CharField(max_length=34, blank=True)
    bic = models.CharField(max_length=11, blank=True)
    line_items = models.JSONField(default=list, blank=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_invoices",
    )
    paid_override = models.BooleanField(
        default=False,
        help_text="When true, treat invoice as paid without full payment transaction coverage.",
    )
    
    class Meta:
        # Note: unique_together with nullable fields is tricky, consider using UniqueConstraint instead
        ordering = ['-invoice_date', '-created_at']
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
    
    def __str__(self):
        entity_name = self.vendor.name if self.vendor else (self.customer.name if self.customer else 'Unknown')
        return f"{self.invoice_number} - {entity_name} ({self.total_amount} {self.currency})"
    
    @property
    def payments_total(self):
        """Sum of settlement allocations (`amount_invoice`) from linked transactions."""
        from decimal import Decimal

        agg = self.settlement_allocations.aggregate(total=models.Sum("amount_invoice"))
        return agg["total"] or Decimal("0")

    @property
    def outstanding_amount(self):
        """`total_amount - payments_total`. Negative if overpaid."""
        return self.total_amount - self.payments_total

    @property
    def is_paid(self):
        """True when the invoice is settled.

        Considered paid when linked payment transactions cover the total or
        when the legacy `payment_date` field is set (kept for backward compat).
        """
        if self.payments_total >= self.total_amount and self.total_amount > 0:
            return True
        if self.paid_override:
            return True
        return self.payment_date is not None

    @property
    def days_overdue(self):
        """Calculate days overdue if payment is late."""
        if self.is_paid:
            return None
        from django.utils import timezone
        today = timezone.now().date()
        if today > self.due_date:
            return (today - self.due_date).days
        return 0
    
    def get_pdf_url(self):
        """Get the URL to access the PDF file."""
        from django.conf import settings
        import os
        
        if not self.file_path:
            return None
        
        # Normalize the path
        file_path = self.file_path
        
        # Check if it's an absolute path
        if os.path.isabs(file_path):
            # If it's within MEDIA_ROOT, make it relative
            if file_path.startswith(settings.MEDIA_ROOT):
                relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
            # If it's within DJANGO_DRF_FILEPOND_FILE_STORE_PATH, make it relative to MEDIA_ROOT
            elif hasattr(settings, 'DJANGO_DRF_FILEPOND_FILE_STORE_PATH') and file_path.startswith(settings.DJANGO_DRF_FILEPOND_FILE_STORE_PATH):
                # The filepond store path might be different, but we'll try to map it
                # For now, if it's in the filepond store, we need to check if it's also in media
                if settings.MEDIA_ROOT in file_path:
                    relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
                else:
                    # Try to construct a path relative to media/invoices
                    filename = os.path.basename(file_path)
                    relative_path = f"invoices/{filename}"
            else:
                # Absolute path outside known directories - try to extract filename
                filename = os.path.basename(file_path)
                relative_path = f"invoices/{filename}"
        else:
            # Already relative path
            relative_path = file_path.lstrip('/')
        
        # Ensure we use forward slashes for URLs
        relative_path = relative_path.replace('\\', '/')
        
        # Return the media URL
        return f"{settings.MEDIA_URL}{relative_path}"


class InvoiceExtraction(BaseModel):
    """
    Model storing raw extraction data and processing metadata.
    """
    invoice = models.OneToOneField(
        Invoice, 
        on_delete=models.CASCADE, 
        related_name='extraction',
        help_text="Associated invoice"
    )
    
    # Raw data
    raw_text = models.TextField(blank=True, help_text="Raw text extracted from PDF")
    raw_extracted_data = models.JSONField(
        default=dict, 
        help_text="Raw JSON data extracted by LLM"
    )
    validated_data = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        help_text="Validated and cleaned data"
    )
    
    # Processing metadata
    extraction_method = models.CharField(
        max_length=50, 
        default='llm',
        help_text="Method used for extraction (llm, regex, manual)"
    )
    confidence_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Confidence score (0-100) for extraction quality"
    )
    field_confidence = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-field confidence scores (0-1), keyed by field name",
    )
    llm_model_name = models.CharField(max_length=120, blank=True)
    prompt_version = models.CharField(max_length=64, blank=True)
    processed_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When extraction was completed"
    )
    
    # Error handling
    retry_count = models.IntegerField(default=0, help_text="Number of retry attempts")
    last_error = models.TextField(blank=True, help_text="Last error message")
    
    class Meta:
        verbose_name = "Invoice Extraction"
        verbose_name_plural = "Invoice Extractions"
    
    def __str__(self):
        return f"Extraction for {self.invoice.invoice_number}"


class InvoiceTemplate(BaseModel):
    """
    Model to store invoice templates with spatial data.
    Templates help identify where fields are located in invoices from specific vendors or for emitted invoices.
    
    - For received invoices: Template is associated with a vendor (vendor uses same template)
    - For emitted invoices: Template is associated with a user (user's company template)
    """
    TEMPLATE_TYPE_CHOICES = [
        ('received', 'Received Invoice Template'),
        ('emitted', 'Emitted Invoice Template'),
    ]
    
    # Template identification
    name = models.CharField(
        max_length=255,
        help_text="Template name/identifier"
    )
    template_type = models.CharField(
        max_length=20,
        choices=TEMPLATE_TYPE_CHOICES,
        default='received',
        help_text="Type of template: received (from vendor) or emitted (to customer)"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the template"
    )
    
    # Relationships
    # For received invoices: template belongs to a vendor
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='invoice_templates',
        help_text="Vendor this template belongs to (for received invoices)"
    )
    # For emitted invoices: template belongs to a user/company
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='invoice_templates',
        help_text="User/company this template belongs to (for emitted invoices)"
    )
    
    # Spatial data - stores coordinates and regions for each field
    spatial_data = models.JSONField(
        default=dict,
        help_text="Spatial information about field locations. Format: {'field_name': {'region': 'top_left', 'coordinates': {...}, 'patterns': [...]}}"
    )
    
    # Template metadata
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this template is active"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the default template for the vendor/user"
    )
    usage_count = models.IntegerField(
        default=0,
        help_text="Number of times this template has been used"
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this template was last used"
    )
    
    # Sample invoice reference (optional)
    sample_invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='template_samples',
        help_text="Reference invoice used to create this template"
    )
    
    class Meta:
        verbose_name = "Invoice Template"
        verbose_name_plural = "Invoice Templates"
        ordering = ['-is_default', '-usage_count', '-created_at']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(vendor__isnull=False, user__isnull=True) |
                    models.Q(vendor__isnull=True, user__isnull=False)
                ),
                name='template_must_have_vendor_or_user'
            )
        ]
    
    def __str__(self):
        if self.vendor:
            return f"{self.name} - {self.vendor.name} (Received)"
        elif self.user:
            return f"{self.name} - {self.user.username} (Emitted)"
        return f"{self.name} ({self.get_template_type_display()})"
    
    def clean(self):
        """Validate that either vendor or user is set, but not both."""
        from django.core.exceptions import ValidationError
        if not self.vendor and not self.user:
            raise ValidationError("Template must have either a vendor (for received) or user (for emitted)")
        if self.vendor and self.user:
            raise ValidationError("Template cannot have both vendor and user")
    
    def save(self, *args, **kwargs):
        """Ensure only one default template per vendor/user."""
        self.clean()
        # If this is set as default, unset others
        if self.is_default:
            if self.vendor:
                InvoiceTemplate.objects.filter(vendor=self.vendor, is_default=True).exclude(pk=self.pk).update(is_default=False)
            elif self.user:
                InvoiceTemplate.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
    
    def increment_usage(self):
        """Increment usage count and update last used timestamp."""
        from django.utils import timezone
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])