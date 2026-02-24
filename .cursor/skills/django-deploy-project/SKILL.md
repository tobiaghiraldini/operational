---
name: django-deploy-project
description: Guides deployment of this Django project to production. Use when deploying, going to production, setting up a server, or when the user asks about deployment, hosting, or production configuration.
---

# Deploy Django Project

Guides deployment of the Operational Django 6.0 project (django-tenants, HTMX, Unfold, PostgreSQL) to a production environment.

## When to use

- User asks to deploy, put in production, or set up for production
- User asks about hosting, server setup, or production checklist

## Pre-deployment checklist

1. **Settings**: Use environment variables for `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `DATABASE_URL` (or DB config). No hardcoded secrets in repo.

2. **Static/media**: Run `collectstatic` and configure the app server or CDN to serve static files. Set `STATIC_ROOT` and `STATIC_URL` (and `MEDIA_*` if used).

3. **Database**: PostgreSQL recommended. Run migrations on the target DB:
   - Public schema: `python manage.py migrate`
   - Tenant schemas: `python manage.py migrate_schemas` (django-tenants)

4. **WSGI/ASGI**: Use a production ASGI/WSGI server (e.g. Gunicorn with uWSGI or Daphne for ASGI). Point to the project’s `operational.asgi` or `operational.wsgi` application.

5. **Multi-tenancy**: Ensure tenant domains are created and `TENANT_DOMAIN_MODEL` / `TENANT_MODEL` match production (e.g. `customers.Client`, `customers.Domain`). Middleware order: `TenantMainMiddleware` first so request is bound to the correct schema.

6. **HTTPS**: Use TLS in front of the app (reverse proxy or load balancer). Set `SECURE_*` and `SESSION_COOKIE_SECURE` etc. for production.

7. **HTMX**: No special deployment steps; ensure CSRF and session cookies work across the same origin and that partial responses are not cached inappropriately (headers as needed).

## Common deployment targets

- **Single server**: Nginx (or Caddy) → Gunicorn/uWSGI → Django. Static via Nginx or same app with whitenoise.
- **PaaS** (e.g. Heroku, Railway, Render): Set buildpack/command to run Gunicorn; set env vars; run migrations in release phase.
- **Containers**: Dockerfile runs migrations then starts Gunicorn/ASGI server; orchestration (e.g. Kubernetes) handles scaling.

## Commands to run on deploy

```bash
python manage.py migrate
python manage.py migrate_schemas   # if using django-tenants
python manage.py collectstatic --noinput
# Then start application server (e.g. gunicorn operational.wsgi:application)
```

## Reference

- Django 6.0 deployment: `mcp_context7_query-docs` with `/websites/djangoproject_en_6_0`
- django-tenants: `/websites/django-tenants_readthedocs_io_en` (production, schema handling)
