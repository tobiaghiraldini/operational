from django.db import models


class Plan(models.Model):
    """Plan: named container (e.g. Q1 2026) for milestones. Tenant-scoped."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "plans_plan"
        ordering = ["-start_date", "name"]
        verbose_name = "Plan"
        verbose_name_plural = "Plans"

    def __str__(self):
        return self.name
