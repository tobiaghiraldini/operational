---
name: django-create-app
description: Creates a new Django app under apps/ and wires it into the project. Use when adding a new app, scaffolding an app, or when the user asks to create a Django application.
---

# Create Django App

Creates a new Django app in `apps/<app_name>/` and registers it in settings and URLs as appropriate for this project (Django 6.0, django-tenants).

## When to use

- User asks to create a new app or "add an app"
- Scaffolding a feature that needs its own app under `apps/`

## Steps

1. **Create the app** in `apps/` (not at project root):
   ```bash
   python manage.py startapp <app_name> apps/<app_name>
   ```
   If the directory already exists, create the standard module files: `__init__.py`, `apps.py`, `models.py`, `admin.py`, `views.py`, `urls.py`, `tests.py`, `apps/<app_name>/migrations/__init__.py`.

2. **Set app config** in `apps/<app_name>/apps.py`:
   - Use a clear `name = "apps.<app_name>"` and `verbose_name` as needed.

3. **Register in settings** (`operational/settings.py`):
   - **Shared (public) app**: add `"apps.<app_name>"` to `SHARED_APPS`.
   - **Tenant-specific app**: add `"apps.<app_name>"` to `TENANT_APPS`.
   - Do not duplicate in both; follow existing pattern (e.g. `apps.customers` in SHARED_APPS, `apps.projects` in TENANT_APPS).

4. **Wire URLs**:
   - In `operational/urls.py`, add `path("<prefix>/", include("apps.<app_name>.urls"))` (or the chosen prefix).
   - In `apps/<app_name>/urls.py`, define `urlpatterns` (e.g. empty list initially).

5. **Templates** (optional): create `apps/<app_name>/templates/` if the app will serve HTML; app templates typically live under `apps/<app_name>/templates/`.

## Checklist

- [ ] App lives under `apps/<app_name>/`
- [ ] App added to either `SHARED_APPS` or `TENANT_APPS` in `operational/settings.py`
- [ ] `operational/urls.py` includes the app's URLconf
- [ ] `apps/<app_name>/urls.py` exists with `urlpatterns`

## Reference

- Django 6.0: `mcp_context7_query-docs` with `/websites/djangoproject_en_6_0`
- django-tenants (SHARED_APPS vs TENANT_APPS): `/websites/django-tenants_readthedocs_io_en`
