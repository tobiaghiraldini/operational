---
name: htmx-xhr-flow
description: Implements an HTMX request-response flow (trigger, target, swap) and the matching Django view and partial template. Use when adding HTMX behavior, partial updates, or when the user asks for HTMX, hx-get, hx-post, or dynamic content without full page reload.
---

# HTMX XHR Flow

Implements a complete HTMX flow: trigger in the template, Django view that returns partial HTML, and swap into the page. Project uses Django 6.0, templates in `templates/` and `apps/<app>/templates/`, and vanilla HTMX (no SPA framework).

## When to use

- User asks to add HTMX, partial update, or dynamic content
- User mentions hx-get, hx-post, hx-swap, or "load content without full reload"

## Flow overview

1. **Template**: Add HTMX attributes to an element (e.g. `hx-get`, `hx-post`, `hx-trigger`, `hx-target`, `hx-swap`).
2. **View**: Detect `HX-Request` header; return a **partial** template (fragment) for HTMX and optionally full page for non-HTMX (e.g. first load or fallback).
3. **Partial template**: A small template that renders only the fragment to be swapped in (no full `<html>` or base layout).

## Template (client)

- **Request**: `hx-get` or `hx-post` with the URL (use `{% url 'app:view_name' %}` or path).
- **Trigger**: `hx-trigger="click"`, `submit`, `change`, `revealed`, or custom events.
- **Target**: `hx-target` — CSS selector for the element to update (e.g. `#content`, `next .list`). Omit to update the requesting element.
- **Swap**: `hx-swap="innerHTML"` (default), `outerHTML`, `beforeend`, `afterend`, etc.
- **Optional**: `hx-headers` for extra headers; `hx-vals` for JSON body; `hx-swap-oob="true"` for out-of-band swap.

Example:

```html
<div id="list-container">
  <!-- content replaced by HTMX -->
</div>
<button hx-get="{% url 'myapp:list_partial' %}"
        hx-target="#list-container"
        hx-swap="innerHTML"
        hx-trigger="click">
  Load list
</button>
```

## View (Django)

- Read `request.headers.get("HX-Request")` (or use a helper like `request.htmx` if django-htmx is installed).
- For HTMX requests: return `render(request, "app/partial.html", context)` with status 200 (or 4xx for errors). Do not wrap in base template.
- For non-HTMX (optional): return full page so the page works without JS.

Example:

```python
def list_partial(request):
    items = MyModel.objects.all()[:10]
    if request.headers.get("HX-Request"):
        return render(request, "myapp/partials/list.html", {"items": items})
    return render(request, "myapp/list.html", {"items": items})
```

## Partial template

- Only the fragment that goes into the target (e.g. a `<ul>` or a `<div>`). No `<!DOCTYPE>`, no `{% extends "base.html" %}` for the partial.

Example `myapp/partials/list.html`:

```html
<ul>
  {% for item in items %}
  <li>{{ item.name }}</li>
  {% endfor %}
</ul>
```

## Checklist

- [ ] Template has `hx-get`/`hx-post`, `hx-target`, `hx-swap`, `hx-trigger` as needed
- [ ] View checks `HX-Request` and returns a partial template for HTMX
- [ ] Partial template contains only the fragment (no full page)
- [ ] URL is correct and CSRF is included for POST (e.g. `hx-headers` or form with `{% csrf_token %}`)

## Reference

- HTMX: `mcp_context7_query-docs` with `/bigskysoftware/htmx`
- Django + HTMX: `/spookylukey/django-htmx-patterns`
- Project rule: `frontend-developer.mdc` (HTMX best practices)
