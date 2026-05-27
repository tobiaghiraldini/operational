# Operational: Use Cases vs Existing Apps and Models

This plan maps each use case to current state and required changes.

## Projects vs Products (corrected)

| Concept | App | Role |
|---------|-----|------|
| **Project** | `apps.projects` | Container for work: plans, systems, parts, architecture, tasks, issues, tests. Lifecycle status live/dev/testing. |
| **Product** | `apps.products` | Commercial assets you **buy or license**: Cursor IDE, Creative Tim templates, SaaS seats. Licenses, renewals, subscriptions. |

**Previous docs incorrectly treated Product as project.** See [products_module.md](products_module.md) and [projects_module.md](projects_module.md).

**Current code gap:** [apps/projects/models.py](../apps/projects/models.py) is empty and **not installed**; [apps/products/models.py](../apps/products/models.py) has a `Product` model with **project-like** fields (`status` idea/dev/testing/live) that should move to **Project** when implemented.

---

## Use case 1: Track projects through plans, tasks, integrations, systems, parts, linked knowledge

**Goal:** One place to see a **project** with its plans, tasks, integrations, systems, parts, and linked knowledge. Optionally which **licensed products** (tools) the project uses.

### Current state

| Area | Existing | Missing |
|------|----------|---------|
| **Project** | No `Project` model; projects app not in `TENANT_APPS` | **Project** model; install `apps.projects`; composition relations |
| **Product (commercial)** | `Product` in products app with wrong semantics (lifecycle = project) | Repurpose for vendor/licenses; **ProductLicense**; M2M Project↔Product |
| **Plans** | `Plan`; `Milestone` → Plan | **Project ↔ Plan** M2M |
| **Tasks** | `Task` standalone | **Task ↔ project**, plan, milestone |
| **Integrations** | integrations app empty | **Integration** + optional **project** FK |
| **Systems** | `System` | **Project ↔ System** M2M; Parts GFK → Project or System |
| **Parts** | `Part` GFK → System/**Product** (parent should be **Project**) | Repoint GFK to Project; ApiKey/Credential first-class |
| **Linked knowledge** | `Article` only | Entity links to **Project**, System, etc. |

### Recommended changes (use case 1)

- **Projects**
  - Add **`Project`**: name, slug, description, status (idea/dev/testing/live/archived), owner, topics M2M.
  - **M2M Plan**, **M2M System**, optional **M2M Milestone**.
  - **M2M Product** (licensed tools used on this project, through table with role/notes).
- **Products**
  - Reshape **`Product`** for commercial catalog (vendor, product_kind, URLs).
  - Add **`ProductLicense`**: license_type, seats, dates, renewal, status, optional license key / Part link.
  - Remove project lifecycle from Product; link renewals to **Deadline** and **Money**.
- **Tasks:** FKs `project`, `plan`, `milestone`.
- **Integrations:** optional FK `project`.
- **Systems:** M2M **Project** (not Product).
- **Parts / ApiKey / Credential:** GFK parent **Project** or **System**.
- **Knowledge:** link articles to **Project**, System, Plan, etc.

Result: a **project** aggregates delivery work; **products** track what you paid for and can be attached to projects as tools.

---

## Use case 2: Highlight security concerns (planned checks, API key rotations)

**Goal:** Planned checks and API key rotation tracking with visibility (dashboard, deadlines).

### Current state

| Area | Existing | Missing |
|------|----------|---------|
| **Planned checks** | None | **PlannedCheck** linked to **Project** and/or System |
| **API key rotations** | `Part` type API_KEY; `ServiceCredential` | First-class ApiKey/Credential; rotation fields; Deadline GFK |

### Recommended changes (use case 2)

- **PlannedCheck:** optional FK **Project**, System.
- **ApiKey / Credential:** GFK parent **Project** or System; rotation dates on ApiKey, Credential, ServiceCredential.
- **Part:** Token, Account, License, Other on Project/System; optional `expires_at`.
- **Deadlines:** generic relation to Part, ApiKey, Credential, ServiceCredential.

---

## Use case 3: Populate Knowledge from data, links, PDFs; node-based and view-based UI

**Goal:** Ingest and navigate knowledge; graph includes **projects**, systems, parts, articles.

### Recommended changes (use case 3)

- **KnowledgeRelation:** nodes include **Project**, System, Part, ApiKey, Credential, Article, Topic, Product (commercial), ProductLicense.
- **Articles:** M2M Topics; links to **Project**, System, etc.

---

## Use case 4: Track money flow, reports, and accounting documents

**Goal:** Money flow and accounting; link spend to **projects** and **product licenses**.

### Recommended changes (use case 4)

- **Transaction:** optional FK **`project`** (initiative cost), optional FK **`product_license`** or **product** (subscription renewal).
- **Budget:** optional scope by **project** or category.

---

## Decided: Parts, ApiKey, and Credential (hybrid)

- **Part:** Token, Account, License, Other. Parent: **Project** or System (GFK).
- **ApiKey / Credential:** first-class; parent **Project** or System; rotation fields.
- **Unified UI:** “Parts & keys” per **Project** / System.
- **Deadlines:** GFK to Part, ApiKey, Credential, ServiceCredential.

Commercial **product license keys** may live on **ProductLicense** or a Part linked to **Product** (not Project), unless the key is for runtime of a built system (then Project/System).

---

## Summary: what to add or extend

| App | Add or extend |
|-----|----------------|
| **projects** | **Install app.** `Project` model; M2M Plan, System, Milestone, Product (tools); hub for PM |
| **products** | Repurpose `Product`; **ProductLicense**; vendor/kind; renewals; M2M with Project |
| **plans** | Relation from **Project** |
| **milestones** | Optional M2M from **Project** |
| **tasks** | FKs: project, plan, milestone |
| **integrations** | Integration model; optional **project** FK |
| **systems** | M2M to **Project** |
| **parts** | ApiKey, Credential; GFK → **Project**/System |
| **knowledge** | KnowledgeSource; KnowledgeRelation; Article links |
| **deadlines** | Generic relation to expirable/rotatable entities |
| **services** | Rotation on ServiceCredential; scope by project where relevant |
| **money** | Transaction → project, product_license |
| **architecture** (new) | Profile per **Project** |
| **checks** (optional) | PlannedCheck → **Project**/System |

---

## Suggested implementation order

1. **Projects + Products split:** Install projects; add Project; reshape Product + ProductLicense; migrate misplaced fields off Product.
2. **Use case 1:** Project–Plan–Task–System–Integrations–Knowledge links.
3. **Use case 2:** ApiKey/Credential, deadlines, planned checks.
4. **Use case 3:** Knowledge graph relations.
5. **Use case 4:** Money links to project and product licenses.

See [operational_project_plan.md](operational_project_plan.md) and the [project management features plan](../../.cursor/plans/project_management_features_10041c5f.plan.md).
