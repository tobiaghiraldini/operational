---
name: Operational high-level plan and docs
overview: Define documentation structure (plans vs dev), ideate features for all ten modules from operational-requirements.md (Plan, Products, Systems, Parts, Topics, Knowledge, Tasks, Deadlines, Money, Accounting), and specify where to store high-level plans and implementation details with Mermaid diagrams for architecture, APIs, DB, flows, and decision trees.
todos: []
isProject: false
---

# Operational — High-Level Project Plan and Documentation Structure

## Current state

- **Requirements:** [docs/requirements/operational-requirements.md](docs/requirements/operational-requirements.md) lists 10 modules: Plan, Products, Systems, **Parts**, **Topics**, Knowledge, Tasks, Deadlines, Money, Accounting. Deadlines cover “anything that makes sense” (products, plans, payments, expiring tokens/accounts); Money includes budgets, trends, graphs.
- **Docs today:** [docs/plans/homepage_design.md](docs/plans/homepage_design.md) exists; no `docs/dev/` yet.
- **Stack:** Django 6.0, django-tenants, HTMX, Unfold admin, PostgreSQL (from [.cursor/rules/00-agents-overview.mdc](.cursor/rules/00-agents-overview.mdc)).

---

## 1. Documentation structure


| Location        | Purpose                                             | Contents                                                                                                                                                                                                                       |
| --------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **docs/plans/** | High-level plans, scope, architecture, feature sets | One master project plan; one plan per module (or per major feature). Mermaid: architecture, module interactions, decision trees, high-level flows.                                                                             |
| **docs/dev/**   | Implementation details for builders                 | One file per plan (or per sub-feature): API contracts, DB schema/queries, request/response shapes, data transformations, sequence diagrams, background tasks structures and orchestration. Linked from the corresponding plan. |


**Convention:** For each module (e.g. Tasks), create `docs/plans/tasks_module.md` (plan + feature list + high-level diagrams) and `docs/dev/tasks_module.md` (or split by feature, e.g. `docs/dev/tasks_api_and_models.md`) with implementation details and more technical Mermaid diagrams.

---

## 2. Master plan document (to create)

**File:** `docs/plans/operational_project_plan.md`

- **Sections:** Vision (from requirements intro); module overview table (name, one-line goal, link to module plan); cross-cutting concerns (multi-tenancy, auth, HTMX strategy); roadmap (phases/MVF if you want).
- **Diagrams (Mermaid):**
  - **System context:** Tenant → Operational app → modules (Plan, Products, Systems, Parts, Topics, Knowledge, Tasks, Deadlines, Money, Accounting) and external systems (e.g. bank, tax).
  - **Module dependency graph:** Which modules depend on which (e.g. Tasks/Deadlines reference Products; Parts belong to Systems/Products; Topics tag Knowledge, Products, Parts, Systems; Deadlines may reference expiring Parts; Money/Accounting share entities).
  - **High-level request flow:** Browser → Django (tenant resolution) → app (HTMX vs full page) → module → DB.

This gives a single place to see “what Operational is” and how the modules relate before diving into each module.

---

## 3. Feature ideation per module

Below is a concise feature set per module for you to integrate with your own thoughts. Each bullet is an area to expand in the module plan and, where needed, in `docs/dev/`.

### Plan — “Improvisation kills outcomes”

- **Goals and outcomes:** Define goals (quarterly/yearly), outcomes, success criteria; link outcomes to products/projects.
- **Plans and timelines:** Create plans (e.g. Q1 plan) with time bounds; attach to goals; optional Gantt-style or timeline view.
- **Dependencies and risks:** Mark dependencies between plans or outcomes; simple risk/blocker flags.
- **Dashboard:** Overview of active plans, progress, and next actions (could feed from Tasks).

### Products — “Projects or other types of products”

- **Product types:** Support multiple types (project, product, service, internal initiative) with configurable fields or tags.
- **Lifecycle and status:** Status workflow (e.g. idea → active → done → archived); optional phases/milestones.
- **Linking:** Link products to Systems (e.g. “runs on system X”), Knowledge articles, Tasks, and Deadlines.
- **List and filters:** List products with filters (type, status, owner); tenant-scoped.

### Systems — “Make it worth it and reusable”

- **System registry:** Register systems (apps, services, infra, app layers and modules) with name, type, owner, env (prod/staging).
- **Scope:** Define a system scope, topic and options.
- **Dependencies and topology:** Define “system A depends on system B”; optional diagram or tree view.
- **Runbooks and links:** Attach runbooks (or link to Knowledge); links to dashboards, logs, repos.
- **Reuse:** “Used by” products or other systems; impact view (what breaks if this fails).
- **Linking:** Link systems to Parts (e.g. which tokens/accounts this system uses), Topics.

### Parts — “Every small part deserves its own space and tracing”

- **Part types:** Tokens, accounts, API keys, credentials, licenses, or other “small” assets that belong to something (system, product, team).
- **Ownership and parent:** Each part belongs to a parent (System, Product, or optional generic entity); trace who/what owns it.
- **Sensitive handling:** Optional masking in UI; audit who accessed or rotated; link to expiring Deadlines (e.g. token expiry).
- **Discovery:** List parts by parent, type, or Topic; “where is this key used?” view.

### Topics — “Main concepts that define knowledge, products, parts, systems”

- **Topic registry:** Create topics as first-class concepts (e.g. “Auth”, “Billing”, “Onboarding”); short name, description.
- **Tagging:** Attach topics to Knowledge articles, Products, Parts, Systems (many-to-many); optional to other entities (Tasks, Deadlines) for filtering.
- **Navigation and filter:** Browse by topic; filter lists (products, systems, parts, knowledge) by topic; topic-based dashboards or landing pages.
- **Consistency:** One place to define “what we care about”; avoid duplicate or ad-hoc tags.

### Knowledge — “Don’t lose any knowledge”

- **Articles and structure:** Create/edit articles; hierarchy (e.g. folders/categories) or tags; rich text or Markdown.
- **Relations:** Link articles to Systems, Products, Parts, Topics, Tasks, Deadlines (and vice versa); “related” and “part of” relationships.
- **Search and discovery:** Full-text search; filters by type, tag, linked entity; tenant-scoped.
- **Versioning and history:** Optional version history or “last updated”; who changed what.

### Tasks — “Get sh!t done and organized”

- **Task CRUD:** Title, description, status (e.g. todo/in progress/done), priority, assignee, due date.
- **Grouping:** Lists or boards (e.g. per product, per sprint); optional subtasks.
- **Links:** Link tasks to Products, Systems, Parts, Topics, Knowledge, Deadlines.
- **HTMX flows:** Inline create/edit, status updates, filters without full reload.

### Deadlines — “Don’t forget, don’t do twice”

- **Deadline entity:** Type (payment, contract, renewal, compliance, **expiring token/account**, product milestone, plan milestone), due date, amount if applicable, status (pending/done/overdue).
- **Reminders:** Optional reminder rules (e.g. 7 days before); notifications or dashboard widget.
- **Linking:** Link to Money (invoices), Products, Plans, Tasks, **Parts** (e.g. API key or account expiry); avoid double entry.
- **Status check:** Mark done; list overdue and upcoming; simple dashboard; optional “expiring soon” for Parts.

### Money — “Expenses and earnings, budgets, trends, graphs”

- **Transactions:** Record income and expenses; amount, date, category, counterparty, optional attachment.
- **Categories and tags:** Configurable categories; tags for filtering and reporting.
- **Budgets:** Define budgets (by category, product, or period); track spend vs budget; alerts when approaching or exceeding.
- **Linking:** Link to Products, Deadlines (e.g. invoice), optional to Tasks.
- **Reporting and viz:** Time-range totals, by category; **trends over time**; **graphs/charts** (e.g. monthly comparison, category breakdown); export (CSV) for accounting.

### Accounting — “Tax reporting tool”

- **Fiscal data:** Periods, chart of accounts (or simplified categories), tax-relevant flags.
- **Input from Money:** Consume transactions from Money (or shared model); map to accounting categories.
- **Reports:** Tax-oriented reports (e.g. by period, by category); export for accountant or authority.
- **Audit trail:** Who entered/changed what and when (for compliance).

---

## 4. Per-module plan document (template)

**File:** `docs/plans/<module>_module.md` (e.g. `tasks_module.md`).

Suggested sections:

1. **Purpose and scope** — One paragraph; in/out of scope.
2. **User roles** — Who uses it (e.g. team member, admin, accountant).
3. **Feature list** — From the ideation above, refined with your choices; priorities (MVP vs later).
4. **Architecture (Mermaid)** — Module’s place in the app; main Django apps/models; HTMX vs full page.
5. **Module/layer interactions (Mermaid)** — How this module talks to others (e.g. Tasks → Products, Deadlines → Money).
6. **Key flows** — 1–2 main user flows (e.g. “Create task from product page”); optional high-level sequence or flowchart.
7. **Decision trees (Mermaid)** — e.g. “When to create a task vs a deadline”; status transitions; “Link to product or not”.
8. **Links to dev** — Pointer to `docs/dev/<module>_*.md` for API, DB, and implementation details.

---

## 5. Per-module dev document (template)

**File:** `docs/dev/<module>_*.md` (e.g. `tasks_api_and_models.md`).

Suggested contents:

1. **Data model (conceptual or ER)** — Main entities; Mermaid ER or class diagram.
2. **API / HTTP surface** — URLs, methods, HTMX endpoints; request/response shapes (for critical flows).
3. **DB queries and performance** — Main queries (list, detail, filters); tenant isolation; indexes to consider.
4. **Data transformations (Mermaid)** — e.g. “Form submit → model fields → validation → save”; “Import from Money → Accounting”.
5. **Request/response (Mermaid)** — Sequence diagram: Browser → View → Form/Query → DB → Template/Partial → Response.
6. **Edge cases and security** — Tenant scoping, validation, permissions; reference to analyst notes if any.

---

## 6. Diagram types summary


| Doc type        | Suggested Mermaid diagrams                                                                               |
| --------------- | -------------------------------------------------------------------------------------------------------- |
| **Master plan** | System context, module dependency graph, high-level request flow                                         |
| **Module plan** | Architecture (components/layers), module interactions, decision trees, optional high-level sequence/flow |
| **Module dev**  | ER or class diagram, data transformation flow, request/response sequence, DB query flow (if complex)     |


Use the Mermaid syntax rules from your instructions (no spaces in node IDs, quoted edge labels, no reserved words as IDs, no inline colors).

---

## 7. Suggested order of work

1. **Create folders:** Ensure `docs/plans/` and `docs/dev/` exist.
2. **Master plan:** Add `docs/plans/operational_project_plan.md` with vision, module table, cross-cutting concerns, and the three Mermaid diagrams.
3. **Module plans:** Add one `docs/plans/<module>_module.md` per module (Plan, Products, Systems, Parts, Topics, Knowledge, Tasks, Deadlines, Money, Accounting) with the feature list (merged with your thoughts), scope, and high-level diagrams.
4. **Dev docs:** Add `docs/dev/<module>_*.md` as you start implementation of each module, with implementation-level diagrams.
5. **Requirements doc:** Optionally add a short “Feature summary” section to [docs/requirements/operational-requirements.md](docs/requirements/operational-requirements.md) that links to each module plan for traceability.

---

## 8. Out of scope for this plan

- Actual implementation (Django apps, models, views, migrations).
- Unfold admin customization per module (can be noted in dev docs when you implement).
- Auth and permission model details (to be decided and documented in master plan or a dedicated auth plan).
- Deployment and infra (covered by existing deploy skill/docs).

This structure keeps high-level ideation and architecture in `docs/plans/`, implementation details in `docs/dev/`, and gives you a clear place to merge in your own feature ideas and priorities per module.