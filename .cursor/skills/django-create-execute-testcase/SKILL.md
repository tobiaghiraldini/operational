---
name: django-create-execute-testcase
description: Creates and runs Django TestCase classes for views, models, or APIs. Use when writing tests, adding test cases, running tests, or when the user asks to test Django code.
---

# Create and Execute Django TestCase

Creates Django test cases using `django.test.TestCase` (or `TransactionTestCase` when needed) and runs them. Aligns with project layout: apps in `apps/`, multi-tenancy (SHARED_APPS vs TENANT_APPS), and HTMX where relevant.

## When to use

- User asks to add tests, write tests, or create a test case
- User asks to run tests or run pytest/django test
- After implementing a view or model that should be covered by tests

## Creating tests

1. **Location**: Tests live in `apps/<app>/tests.py` or `apps/<app>/tests/` (e.g. `tests/test_views.py`, `tests/test_models.py`). Prefer the package form for larger apps.

2. **Base class**: Use `django.test.TestCase` for most tests (wraps each test in a transaction). Use `django.test.TransactionTestCase` only when you need to test transaction behavior or use threading.

3. **Structure**:
   - One class per area (e.g. `ViewTests`, `ModelTests`).
   - Method names: `test_<behavior>` (e.g. `test_list_returns_200`, `test_htmx_returns_partial`).

4. **Multi-tenancy**: For tenant-scoped behavior, create a tenant (or use existing tenant/schema) in `setUp` if needed. Tenant model: `customers.Client`; domain model: `customers.Domain`. Use the project's tenant utilities or fixtures if present.

5. **HTMX**: When testing views that return partials for HTMX, set the `HX-Request: true` header in the request and assert on status code and content (e.g. partial HTML, not full page).

## Example

```python
from django.test import TestCase, Client
from django.urls import reverse

class MyViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("myapp:my-view"))
        self.assertEqual(response.status_code, 200)

    def test_htmx_returns_partial(self):
        response = self.client.get(
            reverse("myapp:my-view"),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        # Assert partial content, not full page
```

## Running tests

```bash
# All tests
python manage.py test

# One app
python manage.py test apps.<app_name>

# One test class or method
python manage.py test apps.<app_name>.tests.MyViewTests.test_get_returns_200
```

## Checklist

- [ ] Test file in `apps/<app>/tests.py` or `apps/<app>/tests/`
- [ ] Uses `TestCase` (or `TransactionTestCase` only when needed)
- [ ] Test names describe behavior (`test_...`)
- [ ] For HTMX views, tests cover both full-page and HX-Request responses if applicable
- [ ] Run `python manage.py test` and fix any failures

## Reference

- Django 6.0 testing: `mcp_context7_query-docs` with `/websites/djangoproject_en_6_0`
- django-tenants testing: `/websites/django-tenants_readthedocs_io_en`
