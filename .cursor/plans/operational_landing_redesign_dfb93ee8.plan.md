---
name: operational landing redesign
overview: Redesign the Operational landing page with a Sierra-inspired light UI, gradient typography inspired by MusicChartsAI, and richer content architecture covering all Operational business areas. Implement via a proper Tailwind build pipeline and update homepage documentation in sync.
todos:
  - id: audit-current-home
    content: Audit current homepage implementation and identify reusable sections/interactions.
    status: completed
  - id: setup-tailwind-build
    content: Add Tailwind build pipeline and wire generated CSS into homepage template.
    status: completed
  - id: rebuild-structure-copy
    content: Rebuild landing page structure and complete content for all platform areas plus suggested missing areas.
    status: completed
  - id: apply-visual-system
    content: Implement light-first Sierra-inspired shapes, modern palette, and gradient typography treatments.
    status: completed
  - id: responsive-accessibility-pass
    content: Tune responsive behavior, contrast, focus states, and reduced-motion handling.
    status: completed
  - id: sync-homepage-docs
    content: Update docs/plans/homepage_design.md to match final homepage implementation.
    status: completed
  - id: final-validation
    content: Run project checks and perform manual QA pass across breakpoints.
    status: completed
isProject: false
---

# Operational.cloud Landing Redesign Plan

## Scope
- Redesign the landing page in a modern, captivating style using:
  - Sierra-inspired decorative background color-shapes.
  - MusicChartsAI-style gradient headings/text accents.
  - HTML5 + Tailwind (build pipeline, not CDN).
- Replace current sparse copy/sections with a complete narrative for a multitenant company management platform.
- Keep homepage docs aligned with implementation updates.

## Key Files To Change
- [`/Users/tobia/Code/Projects/NinjaBit/Operational/Web/Backend/Django/6.0/operational/templates/index.html`](/Users/tobia/Code/Projects/NinjaBit/Operational/Web/Backend/Django/6.0/operational/templates/index.html)
- [`/Users/tobia/Code/Projects/NinjaBit/Operational/Web/Backend/Django/6.0/operational/static/css/home.css`](/Users/tobia/Code/Projects/NinjaBit/Operational/Web/Backend/Django/6.0/operational/static/css/home.css) (or replaced by compiled Tailwind output)
- [`/Users/tobia/Code/Projects/NinjaBit/Operational/Web/Backend/Django/6.0/operational/static/js/home.js`](/Users/tobia/Code/Projects/NinjaBit/Operational/Web/Backend/Django/6.0/operational/static/js/home.js)
- [`/Users/tobia/Code/Projects/NinjaBit/Operational/Web/Backend/Django/6.0/operational/docs/plans/homepage_design.md`](/Users/tobia/Code/Projects/NinjaBit/Operational/Web/Backend/Django/6.0/operational/docs/plans/homepage_design.md)
- New Tailwind setup files (to be added): `package.json`, `tailwind.config.js`, `postcss.config.js`, Tailwind input stylesheet, compiled output stylesheet.

## Information Architecture And Content Plan
- **Hero**
  - H1: clear value proposition for Operational as a multitenant company management platform.
  - Supporting paragraph: unify finance, management, operations, R&D, publishing in one workspace.
  - Primary CTA: `Request Demo` (or `Get Started` depending on business intent).
  - Secondary CTA: `See Platform Areas`.
- **Trust / Proof strip**
  - 3-4 stat chips (e.g., teams onboarded, active projects, process coverage) using placeholder metrics until real numbers are provided.
- **Platform Areas grid (core section)**
  - Finance
  - Management
  - Operations
  - Research & Development
  - Publishing
  - Additional suggested areas (missing and high-value):
    - **Compliance & Governance** (audit trails, policies, approvals)
    - **People & Access** (roles, permissions, tenant/user controls)
    - **Integrations & Automation** (external services, sync jobs, workflows)
    - **Knowledge & Decisions** (SOPs, docs, architecture decisions)
- **How it works (3 steps)**
  - Connect your company context.
  - Structure workflows by area.
  - Monitor execution and outcomes.
- **Benefits / outcomes section**
  - Improved visibility, reduced context switching, stronger governance, reusable operational knowledge.
- **Final CTA section + footer**
  - Strong conversion section with gradient heading and modern visual shapes.

## UI/Style Direction (Light-First)
- **Visual baseline**: Sierra-like clean light canvas with layered abstract background blobs/shapes.
- **Brand accents**: gradient text for major headings and key metrics (MusicChartsAI-inspired treatment).
- **Palette strategy**:
  - Light neutrals for page background/surfaces.
  - 2-3 accent hues for gradients and shape layers.
  - Higher-contrast text for accessibility.
- **Components**:
  - Rounded cards with soft borders/shadows.
  - Gradient badges/chips for area labels.
  - Subtle micro-interactions on hover/focus.
- **Responsiveness**:
  - Mobile-first spacing and type scale.
  - Shape density reduced on small screens for clarity/performance.

## Technical Execution Flow
```mermaid
flowchart TD
  discover[Audit current homepage assets] --> setup[Set up Tailwind build pipeline]
  setup --> tokens[Define color and typography tokens]
  tokens --> layout[Rebuild index sections with semantic HTML]
  layout --> visuals[Add Sierra-style background shapes]
  visuals --> gradients[Add gradient heading treatment]
  gradients --> interactions[Refine JS interactions and motion]
  interactions --> docs[Update homepage design documentation]
  docs --> validate[Run lint/build/manual responsive checks]
```

## Risks And Guardrails
- Existing homepage currently uses custom CSS + GSAP/Flubber; migration to Tailwind must avoid visual regressions and unnecessary JS complexity.
- Keep decorative shapes non-intrusive and accessible (proper contrast, no text-obscuring overlays).
- Respect reduced-motion preferences and keep animation optional/subtle.
- Ensure copy remains scannable and conversion-focused (avoid overly generic marketing text).

## Validation Criteria
- Tailwind build works locally and generated CSS is loaded correctly by Django staticfiles.
- Landing visually matches requested style direction (Sierra structure + modern gradients).
- All key platform areas are represented with concise, clear messaging.
- Mobile/tablet/desktop layouts are stable.
- `homepage_design.md` reflects final structure, styling system, and implementation notes.
