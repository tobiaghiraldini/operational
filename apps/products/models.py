from django.db import models


class Product(models.Model):
    """Product: project or product type; made of plans, milestones, systems, parts. Tenant-scoped."""

    class Status(models.TextChoices):
        IDEA = "idea", "Idea"
        DEV = "dev", "Dev"
        TESTING = "testing", "Testing"
        LIVE = "live", "Live"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IDEA,
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
