"""Dashboard data for project management summary widget."""

from django.db.models import Count, Q

from apps.issues.models import Issue
from apps.operations.models import OperationalSnapshot
from apps.projects.models import Project
from apps.testing.models import TestRun, TestScenario


def project_summary_widget_data(user=None):
    """
    Return summary dict for the projects dashboard widget.

    Optional ``user`` reserved for future per-user filtering.
    """
    _ = user
    projects = Project.objects.exclude(status=Project.Status.ARCHIVED)
    latest_snapshots = {}
    for snap in OperationalSnapshot.objects.filter(
        project_id__in=projects.values_list("pk", flat=True)
    ).order_by("project_id", "-recorded_at"):
        if snap.project_id not in latest_snapshots:
            latest_snapshots[snap.project_id] = snap

    open_issues = (
        Issue.objects.filter(
            project__in=projects,
            status__in=[Issue.Status.OPEN, Issue.Status.IN_PROGRESS],
        )
        .values("project_id")
        .annotate(count=Count("id"))
    )
    issue_counts = {row["project_id"]: row["count"] for row in open_issues}

    failing_tests = (
        TestRun.objects.filter(
            outcome=TestRun.Outcome.FAIL,
            scenario__project__in=projects,
            scenario__is_active=True,
        )
        .values("scenario__project_id")
        .annotate(count=Count("id"))
    )
    fail_counts = {row["scenario__project_id"]: row["count"] for row in failing_tests}

    items = []
    for project in projects[:20]:
        snap = latest_snapshots.get(project.pk)
        items.append(
            {
                "id": project.pk,
                "name": project.name,
                "slug": project.slug,
                "status": project.status,
                "live_status": snap.overall_status if snap else None,
                "open_issues": issue_counts.get(project.pk, 0),
                "failing_tests": fail_counts.get(project.pk, 0),
            }
        )

    return {
        "total_projects": projects.count(),
        "by_status": dict(
            projects.values("status").annotate(c=Count("id")).values_list("status", "c")
        ),
        "projects": items,
        "licenses_expiring_soon": _licenses_expiring_soon(),
    }


def _licenses_expiring_soon(days=30):
    from datetime import timedelta

    from django.utils import timezone

    from apps.products.models import ProductLicense

    cutoff = timezone.now().date() + timedelta(days=days)
    return list(
        ProductLicense.objects.filter(
            status=ProductLicense.Status.ACTIVE,
            ends_at__isnull=False,
            ends_at__lte=cutoff,
        )
        .select_related("product")
        .order_by("ends_at")[:10]
        .values("id", "product__name", "ends_at", "license_type")
    )
