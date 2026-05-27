from django.db import models

from apps.core.db.tenant_user_foreign_key import TenantUserForeignKey


class Project(models.Model):
    """Project: container for plans, systems, architecture, tasks, and operational work."""

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
    owner = TenantUserForeignKey(
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_projects",
    )
    topics = models.ManyToManyField(
        "topics.Topic",
        blank=True,
        related_name="projects",
    )
    plans = models.ManyToManyField(
        "plans.Plan",
        blank=True,
        related_name="projects",
    )
    systems = models.ManyToManyField(
        "systems.System",
        blank=True,
        related_name="projects",
    )
    milestones = models.ManyToManyField(
        "milestones.Milestone",
        blank=True,
        related_name="projects",
    )
    commercial_products = models.ManyToManyField(
        "products.Product",
        through="products.ProjectProduct",
        blank=True,
        related_name="projects",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "projects_project"
        ordering = ["name"]
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def __str__(self):
        return self.name
