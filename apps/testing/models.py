from django.db import models

from apps.core.db.tenant_user_foreign_key import TenantUserForeignKey


class TestScenario(models.Model):
    """Defined test case for a project."""

    class Kind(models.TextChoices):
        MANUAL = "manual", "Manual"
        E2E = "e2e", "End-to-end"
        INTEGRATION = "integration", "Integration"
        SMOKE = "smoke", "Smoke"

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="test_scenarios",
    )
    system = models.ForeignKey(
        "systems.System",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="test_scenarios",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.MANUAL,
    )
    steps = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "testing_test_scenario"
        ordering = ["project", "title"]
        verbose_name = "Test scenario"
        verbose_name_plural = "Test scenarios"

    def __str__(self):
        return self.title


class TestRun(models.Model):
    """Outcome of running a test scenario."""

    class Outcome(models.TextChoices):
        PASS = "pass", "Pass"
        FAIL = "fail", "Fail"
        SKIP = "skip", "Skip"
        BLOCKED = "blocked", "Blocked"

    scenario = models.ForeignKey(
        TestScenario,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    run_at = models.DateTimeField(auto_now_add=True)
    outcome = models.CharField(
        max_length=20,
        choices=Outcome.choices,
    )
    notes = models.TextField(blank=True)
    run_by = TenantUserForeignKey(
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="test_runs",
    )
    evidence_url = models.URLField(blank=True)

    class Meta:
        db_table = "testing_test_run"
        ordering = ["-run_at"]
        verbose_name = "Test run"
        verbose_name_plural = "Test runs"

    def __str__(self):
        return f"{self.scenario} @ {self.run_at} ({self.outcome})"
