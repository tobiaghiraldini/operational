# Operational Homepage — Design and Implementation Plan

## Overview

Landing page redesigned to a light-first, modern aesthetic inspired by Sierra (shape-based decorative backgrounds) and MusicChartsAI (gradient headline accents), implemented with a Tailwind build pipeline.

## Implementation status

**Done:**

- [templates/index.html](templates/index.html) — Full semantic landing page rebuilt with:
  - Sticky/scroll-reactive header.
  - Hero with clear value proposition and dual CTAs.
  - Proof strip.
  - Platform areas grid with all core + suggested missing areas.
  - Workflow section (3-step narrative).
  - Benefits section and final CTA.
  - Lightweight footer.
- [static/css/tailwind.input.css](static/css/tailwind.input.css) — Tailwind source with:
  - `@import "tailwindcss";`
  - content `@source` directives for templates and JS.
  - custom utilities (`text-gradient-brand`, `bg-gradient-brand`, `bg-grid-soft`).
- [static/css/home.css](static/css/home.css) — Generated Tailwind output for production/static serving.
- [static/js/home.js](static/js/home.js) — Header scroll behavior:
  - Adds/removes translucent shell classes on scroll.
  - No animation library dependency.
- [package.json](package.json), [tailwind.config.js](tailwind.config.js), [postcss.config.js](postcss.config.js) — Tailwind/PostCSS pipeline.

## Post-launch improvements (implemented)

1. **Tailwind build pipeline**
   - Added npm scripts:
     - `npm run build:css`
     - `npm run watch:css`
   - Compiles from `static/css/tailwind.input.css` to `static/css/home.css`.

2. **Visual modernization**
   - Light neutral base with colorful layered SVG shapes and subtle grid texture.
   - Gradient typography accents for hero/section emphasis.
   - Rounded cards, soft borders, and depth shadows for a cleaner SaaS style.
   - Decorative backgrounds now use visible geometric/blob forms (Sierra-like), not only diffuse blur glows.
   - Final rendition uses Sierra assets directly with section-specific composition:
     - `slider-bg-1.png` for the hero top-right sweep.
     - `3d-slider-shap.png` for the lower section bottom-left shape mass.

3. **Content architecture expansion**
   - Core areas retained and expanded: Finance, Management, Operations, R&D, Publishing.
   - Added missing strategic domains:
     - Compliance & Governance
     - People & Access
     - Integrations & Automation
     - Knowledge & Decisions

4. **Navigation and CTA clarity**
   - Header anchor links to `#areas`, `#workflow`, `#benefits`.
   - Primary CTA appears in hero and final conversion section.

## Homepage structure

- **Header:** Brand, section anchors, login CTA, translucent shell on scroll.
- **Hero:** Primary positioning statement, supporting copy, two CTAs, right-side quick status card.
- **Proof strip:** Four compact trust/value chips.
- **Areas grid:** Nine cards covering company-wide operational domains.
- **Workflow section:** Three-step operating model.
- **Benefits section:** Outcome-focused bullet cards + final CTA.
- **Footer:** Concise brand statement and quick links.

## Technical summary

- **Tailwind source:** `static/css/tailwind.input.css`
- **Compiled CSS:** `static/css/home.css`
- **Template:** `templates/index.html`
- **Behavior script:** `static/js/home.js`
- **Build config:** `tailwind.config.js`, `postcss.config.js`, `package.json`
- **Fonts:** Google Fonts (`Plus Jakarta Sans`, `DM Sans`)

## File and dependency summary

| Item | Role |
| --- | --- |
| templates/index.html | Landing markup and content architecture |
| static/css/tailwind.input.css | Tailwind entrypoint + custom utilities |
| static/css/home.css | Compiled homepage stylesheet |
| static/js/home.js | Header scroll interaction |
| tailwind.config.js | Tailwind scan/theme configuration |
| postcss.config.js | PostCSS plugin wiring |
| package.json | Build and watch scripts, frontend dev deps |

## Notes

- Root URL tenant behavior remains unchanged; this update only affects frontend assets/template.
- If copy or metrics are finalized later, update hero/proof cards first to keep above-the-fold messaging current.
