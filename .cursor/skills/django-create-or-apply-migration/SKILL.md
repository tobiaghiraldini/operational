---
name: django-create-or-apply-migration
description: Creates or applies Django migrations for model changes. Use when changing models, adding migrations, running migrate, or when the user asks to create or run database migrations.
---

# Create or Apply Django Migration

Creates new migrations after model changes and applies migrations. This project uses django-tenants (shared vs tenant schemas) and the default Django migration commands.

## When to use

- User has changed `apps/<app>/models.py` and needs a migration
- User asks to run migrations, apply migrations, or create a migration
- After pulling changes that include new migration files

## Creating migrations

1. **After editing models**: Run:
   ```bash
   python manage.py makemigrations [<app_label>]
   ```
   Use the app label (e.g. `customers`, `projects`) when you only changed one app. Migrations are created under `apps/<app>/migrations/`.

2. **Naming**: Let Django generate the name (e.g. `0002_alter_something.py`). Do not edit migration file names; edit only the generated operations if you must customize.

3. **Multi-tenancy**: Apps in `SHARED_APPS` (e.g. `customers`) apply to the public schema. Apps in `TENANT_APPS` (e.g. `projects`) apply to each tenant schema. Run `migrate_schemas` (django-tenants) to apply tenant migrations to all tenant schemas, or use `migrate` for the public schema and tenant migration flow per project docs.

## Applying migrations

**Public (shared) schema:**
```bash
python manage.py migrate
```

**All tenant schemas (django-tenants):**
```bash
python manage.py migrate_schemas
```

**Single tenant (if your project supports it):**
```bash
python manage.py migrate_schemas --tenant=<schema_name>
```

Use the same migration flow the project already uses (check for `migrate_schemas` in docs or scripts).

## Checklist

- [ ] Model changes are saved in `apps/<app>/models.py`
- [ ] `makemigrations` run and new migration file exists under `apps/<app>/migrations/`
- [ ] `migrate` or `migrate_schemas` run as appropriate for this project
- [ ] No manual editing of migration names; only operations if necessary

## Reference

- Django 6.0 migrations: `mcp_context7_query-docs` with `/websites/djangoproject_en_6_0`
- django-tenants migrations: `/websites/django-tenants_readthedocs_io_en` (schemas, `migrate_schemas`)
