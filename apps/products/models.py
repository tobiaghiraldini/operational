from django.db import models


class Product(models.Model):
    """Commercial product or asset bought or licensed (SaaS, templates, IDEs, etc.)."""

    class ProductKind(models.TextChoices):
        SAAS = "saas", "SaaS"
        TEMPLATE_PACK = "template_pack", "Template pack"
        IDE = "ide", "IDE"
        DESIGN_TOOL = "design_tool", "Design tool"
        CLOUD_SERVICE = "cloud_service", "Cloud service"
        ASSET_LIBRARY = "asset_library", "Asset library"
        OTHER = "other", "Other"

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    vendor = models.CharField(max_length=255, blank=True)
    product_kind = models.CharField(
        max_length=30,
        choices=ProductKind.choices,
        default=ProductKind.OTHER,
    )
    description = models.TextField(blank=True)
    homepage_url = models.URLField(blank=True)
    docs_url = models.URLField(blank=True)
    topics = models.ManyToManyField(
        "topics.Topic",
        blank=True,
        related_name="commercial_products",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products_product"
        ordering = ["name"]
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return self.name


class ProductLicense(models.Model):
    """License or subscription for a commercial product."""

    class LicenseType(models.TextChoices):
        PERPETUAL = "perpetual", "Perpetual"
        SUBSCRIPTION = "subscription", "Subscription"
        TRIAL = "trial", "Trial"
        SEAT_BASED = "seat_based", "Seat-based"
        USAGE_BASED = "usage_based", "Usage-based"
        OPEN_SOURCE = "open_source", "Open source"

    class RenewalInterval(models.TextChoices):
        NONE = "none", "None"
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"
        CUSTOM = "custom", "Custom"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"
        TRIAL = "trial", "Trial"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="licenses",
    )
    license_type = models.CharField(
        max_length=20,
        choices=LicenseType.choices,
        default=LicenseType.SUBSCRIPTION,
    )
    seats = models.PositiveIntegerField(null=True, blank=True)
    started_at = models.DateField(null=True, blank=True)
    ends_at = models.DateField(null=True, blank=True)
    renewal_interval = models.CharField(
        max_length=20,
        choices=RenewalInterval.choices,
        default=RenewalInterval.NONE,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField(max_length=3, blank=True)
    license_key_masked = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products_product_license"
        ordering = ["product", "-ends_at"]
        verbose_name = "Product license"
        verbose_name_plural = "Product licenses"

    def __str__(self):
        return f"{self.product.name} ({self.get_license_type_display()})"


class ProjectProduct(models.Model):
    """Links a project to a commercial product used as a tool on that initiative."""

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="project_products",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="project_products",
    )
    role = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "products_project_product"
        unique_together = ("project", "product")
        verbose_name = "Project product"
        verbose_name_plural = "Project products"

    def __str__(self):
        return f"{self.project} uses {self.product}"
