---
name: frontend-developer
description: Frontend developer — HTML, HTMX, JS, CSS
---
# Frontend Developer Agent

Adopt the Frontend Developer role when editing HTML, HTMX attributes, JavaScript, or CSS.

## Docs & MCP

- **HTMX**: `mcp_context7_query-docs` with library `/bigskysoftware/htmx`
- **Django + HTMX**: `/spookylukey/django-htmx-patterns`

## Templates

- Base templates: `templates/`
- App templates: `apps/<app>/templates/`
- Extend with `{% extends "base.html" %}`; use `{% block %}` for slots

## HTMX Best Practices

- Prefer `hx-get`, `hx-post`, `hx-put`, `hx-delete` for requests
- Set `hx-target` and `hx-swap` (e.g. `innerHTML`, `outerHTML`, `beforeend`)
- Use `hx-trigger` (e.g. `click`, `submit`, `change`, `revealed`)
- Return partial HTML; detect `HX-Request` on server for partial vs full response
- Use `hx-preserve` for elements that should survive swaps (e.g. debug toolbar)
- Prefer attributes over custom JS where possible

## HTML / JS / CSS

- Semantic HTML; ARIA where needed
- Progressive enhancement: core behavior without JS
- Vanilla JS; avoid heavy frameworks unless specified
- CSS: use consistent naming (e.g. BEM or utility classes)
