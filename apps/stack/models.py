from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Technology(models.Model):
    """Registry of languages, frameworks, libraries, and tools."""

    class Kind(models.TextChoices):
        LANGUAGE = "language", "Language"
        FRAMEWORK = "framework", "Framework"
        LIBRARY = "library", "Library"
        RUNTIME = "runtime", "Runtime"
        TOOL = "tool", "Tool"
        PATTERN = "pattern", "Pattern"

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.LIBRARY,
    )
    version_label = models.CharField(max_length=100, blank=True)
    homepage_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stack_technology"
        ordering = ["kind", "name"]
        verbose_name = "Technology"
        verbose_name_plural = "Technologies"

    def __str__(self):
        return self.name


class TechnologyUsage(models.Model):
    """Technology used on a project or system."""

    technology = models.ForeignKey(
        Technology,
        on_delete=models.CASCADE,
        related_name="usages",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    role = models.CharField(max_length=100, blank=True)
    version_constraint = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stack_technology_usage"
        ordering = ["technology"]
        verbose_name = "Technology usage"
        verbose_name_plural = "Technology usages"

    def __str__(self):
        return f"{self.technology} on {self.content_object}"
