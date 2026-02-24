---
name: frontend-templating-styles-animations
description: Implements Django templating, CSS styling, and subtle animations for the frontend. Use when working on templates, styling, CSS, animations, or when the user asks for UI polish, transitions, or frontend presentation.
---

# Frontend Templating, Styles, and Animations

Applies Django templates (base and blocks), CSS for layout and appearance, and light animations. Project uses HTML in `templates/` and `apps/<app>/templates/`, vanilla JS, and no heavy frontend framework.

## When to use

- User asks to style something, add CSS, or improve the look
- User asks for animations, transitions, or UI polish
- User asks about template structure, blocks, or partials

## Templating

- **Base**: `templates/base.html` (or project base). Use `{% extends "base.html" %}` in app templates.
- **Blocks**: Define `{% block content %}`, `{% block title %}`, etc. Override in child templates.
- **Partials**: For HTMX or includes, use small templates under e.g. `apps/<app>/templates/<app>/partials/` with no base extend (fragment only).
- **Static**: Use `{% load static %}` and `{% static 'path/to/file.css' %}` for CSS/JS. Static files in `static/` (project) or `apps/<app>/static/` (app).

## Styling (CSS)

- Prefer consistent naming: BEM-like or utility classes. Avoid one-off inline styles for layout.
- Scope: global in `static/css/`; app-specific in `apps/<app>/static/<app>/css/` if needed. Link in base template or per-page.
- Responsiveness: use media queries; keep breakpoints consistent.
- Prefer CSS over JS for layout and visual state (e.g. flexbox/grid, `:focus`, `:hover`).

## Animations

- Prefer **CSS** for transitions and simple animations: `transition`, `animation`, `@keyframes`. Use for hover, focus, loading, or small feedback.
- Keep animations **short** (e.g. 150–300 ms) and **subtle** so the UI stays responsive.
- Prefer `transform` and `opacity` for smooth performance; avoid animating layout-heavy properties (e.g. `width`, `height`) when possible.
- For HTMX: consider `hx-swap-oob` or swap targets so animated elements don’t flash; use `transition` on the swapped container if needed.

Example:

```css
.card {
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  transform: translateY(-2px);
}
```

## Checklist

- [ ] New pages extend base and use blocks correctly
- [ ] Partials (for HTMX) have no base extend and only the fragment
- [ ] CSS is linked via `{% static %}` and naming is consistent
- [ ] Animations are CSS-based, short, and use transform/opacity where possible
- [ ] No heavy JS frameworks unless specified; progressive enhancement preferred

## Reference

- Django templates: `mcp_context7_query-docs` with `/websites/djangoproject_en_6_0`
- Project rule: `frontend-developer.mdc` (HTML, HTMX, CSS, JS conventions)
