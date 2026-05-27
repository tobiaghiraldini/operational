from django.db import models


class Solution(models.Model):
    """ADR-style solution record for a project."""

    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        ACCEPTED = "accepted", "Accepted"
        DEPRECATED = "deprecated", "Deprecated"

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROPOSED,
    )
    problem_summary = models.TextField(blank=True)
    decision_summary = models.TextField(blank=True)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="solutions",
    )
    systems = models.ManyToManyField(
        "systems.System",
        blank=True,
        related_name="solutions",
    )
    topics = models.ManyToManyField(
        "topics.Topic",
        blank=True,
        related_name="solutions",
    )
    article = models.ForeignKey(
        "knowledge.Article",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solutions",
    )
    architecture_profile = models.ForeignKey(
        "architecture.ArchitectureProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solutions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "solutions_solution"
        ordering = ["-updated_at"]
        verbose_name = "Solution"
        verbose_name_plural = "Solutions"

    def __str__(self):
        return self.title
