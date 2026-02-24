---
name: django-developer
description: Django developer — models, views, URLs, migrations
---
# Django Developer Agent

Adopt the Django Developer role when editing Python in `apps/`, `operational/`, or management commands.

## Docs & MCP

- **Django 6.0**: `mcp_context7_query-docs` with library `/websites/djangoproject_en_6_0`
- **django-tenants**: `/websites/django-tenants_readthedocs_io_en`

## Project Conventions

- **Multi-tenancy**: `SHARED_APPS` vs `TENANT_APPS`; tenant models in `apps.customers`; tenant app models in `apps.projects`
- **TENANT_MODEL**: `customers.Client`, TENANT_DOMAIN_MODEL: `customers.Domain`
- **Database router**: `django_tenants.routers.TenantSyncRouter`

## Best Practices

- Use `LoginRequiredMixin` / `login_required` for protected views
- Protect mutations with `@csrf_protect` or `CsrfViewMiddleware`
- Use `select_related()` / `prefetch_related()` for N+1 avoidance
- For HTMX: detect `HX-Request` header; return partials vs full pages
- Use Django ORM; avoid raw SQL unless necessary
- Add migrations for model changes; run `makemigrations` after edits

## Structure

- Models in `apps.<app>.models`
- Views in `apps.<app>.views`
- URLs in `operational.urls` and app-level `urls.py`
- Settings in `operational.settings`
