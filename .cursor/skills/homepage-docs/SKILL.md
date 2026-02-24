---
name: homepage-docs
description: Keep homepage plan in sync when changing the landing page
---
# Homepage plan upkeep

When you modify the **homepage** in any of these files:

- `templates/index.html`
- `static/css/home.css`
- `static/js/home.js`

you **must** update [docs/plans/homepage_design.md](docs/plans/homepage_design.md) to reflect the changes.

- **Implementation status:** Extend the "Done" bullets if you add behaviour or assets; keep file roles accurate.
- **Post-launch improvements:** Add a new numbered item for each new feature or change (e.g. "Header: transparent → rounded on scroll", "Section separators", etc.) with a short technical note (CSS/JS/template).
- **Homepage structure / Technical summary / File summary:** Adjust the prose and tables so they match the current implementation (e.g. fixed header, scroll behaviour, new sections).

Do this in the same change set as the homepage edit so the plan stays the single source of truth for the landing page.
