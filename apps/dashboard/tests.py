from __future__ import annotations

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, SimpleTestCase

from apps.dashboard.views import DashboardOverviewView, DashboardUsageView


class DashboardViewTemplateTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_overview_returns_200(self):
        request = self.factory.get("/dashboard/")
        request.user = AnonymousUser()
        response = DashboardOverviewView.as_view()(request)
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Getting started", response.content)

    def test_usage_returns_200(self):
        request = self.factory.get("/dashboard/usage/")
        request.user = AnonymousUser()
        response = DashboardUsageView.as_view()(request)
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your usage", response.content)
