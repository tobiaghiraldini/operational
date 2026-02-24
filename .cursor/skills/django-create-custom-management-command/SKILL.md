---
name: django-create-custom-management-command
description: Creates a Django custom management command and shows how to run it. Use when adding a management command, creating a custom manage.py command, or when the user asks for a CLI command or script that uses Django ORM/settings.
---

# Create Django Custom Management Command

Adds a new management command under an app so it can be run with `python manage.py <command_name>`.

## When to use

- User asks to add a management command, create a custom command, or a script that must run in Django context (ORM, settings, tenants)

## Steps

1. **Directory**: Create `apps/<app_name>/management/commands/` if it does not exist. Add `__init__.py` in both `management/` and `management/commands/`.

2. **Command module**: Create `apps/<app_name>/management/commands/<command_name>.py`. Use underscores for the filename; the command name will be the filename (e.g. `my_command.py` → `python manage.py my_command`).

3. **Command class**: Define a class inheriting from `django.core.management.base.BaseCommand` and implement `handle(self, *args, **options)`:

   ```python
   from django.core.management.base import BaseCommand

   class Command(BaseCommand):
       help = "Short description of what the command does"

       def add_arguments(self, parser):
           parser.add_argument("--foo", type=str, default="")

       def handle(self, *args, **options):
           # Use self.stdout.write() instead of print
           self.stdout.write(self.style.SUCCESS("Done."))
   ```

4. **Arguments**: Use `add_arguments(self, parser)` for optional/required args. Use `parser.add_argument()` with `type`, `default`, `required`, `help` as needed.

5. **Output**: Prefer `self.stdout.write()` and `self.stderr.write()` over `print()`. Use `self.style.SUCCESS`, `self.style.WARNING`, `self.style.ERROR` for colored output when helpful.

6. **Multi-tenancy**: If the command must run in tenant context, use django-tenants helpers (e.g. run for each tenant or accept a tenant/schema). Tenant model: `customers.Client`; ensure schema is set if running tenant-specific logic.

## Running the command

```bash
python manage.py <command_name> [--foo value]
```

## Checklist

- [ ] Path: `apps/<app_name>/management/commands/<command_name>.py`
- [ ] `management/` and `management/commands/` have `__init__.py`
- [ ] Class named `Command` inheriting from `BaseCommand`
- [ ] `handle(self, *args, **options)` implemented
- [ ] Use `self.stdout`/`self.stderr` for output

## Reference

- Django 6.0 custom commands: `mcp_context7_query-docs` with `/websites/djangoproject_en_6_0`
