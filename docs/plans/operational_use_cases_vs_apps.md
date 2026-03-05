# Operational: Use Cases vs Existing Apps and Models

This plan maps each use case to current state and required changes. **No new top-level apps are strictly necessary**; the existing module set (Products, Plans, Milestones, Tasks, Integrations, Systems, Parts, Knowledge, Deadlines, Services, Money, Accounting) can cover the four use cases after targeted model and relation additions. The **projects** app is empty and marked legacy; the plan treats **Products** as "projects" per [operational_project_plan.md](operational_project_plan.md).

---

## Use case 1: Track projects through plans, tasks, integrations, systems, parts, linked knowledge

**Goal:** One place to see a project (product) with its plans, tasks, integrations, systems, parts, and linked knowledge.

### Current state

| Area                 | Existing                                                                                                                                                            | Missing                                                                                                                             |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **Project**          | [apps/products/models.py](../apps/products/models.py): `Product` (name, slug, status, description). [apps/projects/models.py](../apps/projects/models.py) empty (legacy). | Clarify: use Product as "project"; consider deprecating or repurposing `projects` app.                                              |
| **Plans**            | [apps/plans/models.py](../apps/plans/models.py): `Plan`; [apps/milestones/models.py](../apps/milestones/models.py): `Milestone` → Plan.                                   | **Product ↔ Plan**: no relation. Plan says "many plans per product" — not implemented.                                              |
| **Tasks**            | [apps/tasks/models.py](../apps/tasks/models.py): `Task` (title, status, priority, due_date).                                                                           | **Task ↔ Product, Plan, Milestone**: no FKs. Comment says "Links to products, milestones, etc. (later)".                            |
| **Integrations**     | [apps/integrations/models.py](../apps/integrations/models.py): empty.                                                                                                  | **Integration registry**: e.g. type (Stripe, etc.), link to ExternalService, optional link to Product/tenant.                       |
| **Systems**          | [apps/systems/models.py](../apps/systems/models.py): `System` (name, type, environment).                                                                               | **System ↔ Product**: "used by" not modeled; Parts already attach to System or Product via GenericForeignKey.                       |
| **Parts**            | [apps/parts/models.py](../apps/parts/models.py): `Part` with GenericForeignKey to System/Product.                                                                      | Satisfies "parts per project/system"; Part kept for Token/Account/License/Other; ApiKey and Credential first-class (see below).     |
| **Linked knowledge** | [apps/knowledge/models.py](../apps/knowledge/models.py): `Article` only. [apps/topics/models.py](../apps/topics/models.py): `Topic`.                                      | **Article ↔ Topics / Products / Systems / Parts**: no relations. **Knowledge graph**: no node/relation models yet (see Use case 3). |


### Recommended changes (use case 1)

- **Products**
  - Add **M2M or reverse relation Product ↔ Plan** (e.g. `Plan.product_set` or `Product.plans` M2M) so "projects" can list their plans.
  - Optionally link **Milestone** to Product (M2M or FK) for "milestones tied to this project" beyond plan membership.
- **Tasks**
  - Add optional **FKs**: `Task.product`, `Task.plan`, `Task.milestone` (or generic relation) so tasks are scoped to project/plan/milestone.
- **Integrations**
  - Add at least one model, e.g. **Integration**: type/slug, FK to `ExternalService`, optional FK to `Product`, tenant-scoped; used to "track which integrations this project uses."
- **Systems**
  - Add **M2M Product ↔ System** ("this product uses these systems") so project view can list systems; Parts, ApiKeys, and Credentials already attach to both.
- **Knowledge**
  - Add **linking of Article** to Topics (M2M) and to entities (GenericRelation or M2M to Product, System, Part, ApiKey, Credential, Plan, etc.) so "linked knowledge" for a project is queryable.
- **Projects app**
  - Either **remove** it or document that "project" = Product and use the app only for backward compatibility or future project-specific views; no new models in `projects` required for this use case.

Result: a "project" (Product) can aggregate plans, milestones, tasks, integrations, systems, parts, API keys, credentials, and linked articles via new relations.

---

## Use case 2: Highlight security concerns (planned checks, API key rotations)

**Goal:** Planned checks (security audit, performance, resources) and API key rotation tracking with visibility (e.g. dashboard, deadlines).

### Current state

| Area                  | Existing                                                                                                                                                                                                                                   | Missing                                                                                                                                                                                     |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Planned checks**    | None.                                                                                                                                                                                                                                      | No model for "scheduled check" (security audit, performance, resource consumption) with type, schedule, last run, result, link to Product/System.                                           |
| **API key rotations** | [apps/parts/models.py](../apps/parts/models.py): `Part` (type API_KEY); [apps/services/models.py](../apps/services/models.py): `ServiceCredential`. [apps/deadlines/models.py](../apps/deadlines/models.py): `Deadline` with type `EXPIRING_TOKEN`. | **Rotation state**: no `last_rotated_at` / `next_rotation_due` on ServiceCredential. **First-class ApiKey/Credential** and **Deadline ↔ entity**: see decided hybrid below.              |


### Recommended changes (use case 2)

- **Planned checks**
  - New app **checks** (or **security_checks**) with model **PlannedCheck**: check_type (e.g. security_audit, performance, resources_consumption), schedule (cron or interval), last_run_at, next_run_at, result (status, summary, details JSON), optional FK to Product and/or System. Enables dashboard and reports for "planned checks."
- **Parts (decided: hybrid — see section "Decided: Parts, ApiKey, and Credential")**
  - Add first-class **ApiKey** and **Credential** with `last_rotated_at`, `next_rotation_due`, optional scope/environment, same attachment to System/Product as Part. Keep **Part** for Token, Account, License, Other; add optional **expires_at** on Part for tokens/licenses.
  - Rotation dates live on **ApiKey**, **Credential**, and **ServiceCredential**, not on Part.
- **Services**
  - Add **last_rotated_at** and **next_rotation_due** to **ServiceCredential** for rotation tracking.
- **Deadlines**
  - Add a **generic relation** (ContentType + object_id) to the "expirable or rotatable" entity (Part, ApiKey, Credential, or ServiceCredential) so deadline types like `expiring_token` / `rotation_due` can point at any of them; one deadline list and reminders for all.

Result: planned checks are first-class; rotation is first-class on ApiKey, Credential, and ServiceCredential; Part keeps optional expiry; Deadlines surface "expiring/rotation due" for any linked entity.

---

## Use case 3: Populate Knowledge from data, links, PDFs; node-based (flow) and view-based (parents–children) UI

**Goal:** Ingest from existing data, links, and PDFs; structure knowledge so it can be navigated as a node graph (e.g. React Flow) or as a parent–child view.

### Current state

| Area                  | Existing                                                                               | Missing                                                                                                                                               |
| --------------------- | -------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Content**           | [apps/knowledge/models.py](../apps/knowledge/models.py): **Article** (title, slug, body). | **Sources**: no model for "where this came from" (URL, PDF file, import job). **Article ↔ rest of world**: no Topic or entity links.                  |
| **Graph / structure** | Plan describes React Flow and "what everything is made of."                            | No **nodes** or **relations** tables. Need a way to represent graph nodes (entities or dedicated nodes) and edges.                                    |
| **Parent–child view** | Not implemented.                                                                       | Either explicit parent FK on a node/entity, or a generic **relation** model (source, target, relation_type) that can drive both graph and tree views. |


### Recommended changes (use case 3)

- **Knowledge sources (population)**
  - Add **KnowledgeSource** (or under Core): type (url, pdf, import), url/path reference, optional file storage reference, status (pending/processed/failed), processed_at, optional link to created Article(s) or nodes. Ingestion (fetch, parse, create/update Articles or nodes) can live in Core + Celery; model in Knowledge (or Core) so Knowledge remains the owner of "what we know."
- **Graph and parent–child**
  - Introduce **KnowledgeRelation** (or **KnowledgeEdge**): source ContentType + object_id, target ContentType + object_id, relation_type (e.g. "made_of", "depends_on", "tags"), optional metadata. Nodes = existing entities (Product, System, Part, ApiKey, Credential, Article, Topic) + ContentType. Graph UI (React Flow) and parent–child UI both consume this (parent–child = relation_type or direction). No separate KnowledgeNode table unless virtual nodes are needed later.
- **Articles**
  - Add **M2M to Topics**. Add **GenericRelation** (or M2M) from Article to Products, Systems, Parts, ApiKey, Credential, etc., so articles are part of the same graph and linkable from project views.
- **API**
  - Expose graph payload: list of nodes (entity type + id + label) and edges (from KnowledgeRelation) for React Flow; and a tree/parent–child endpoint (e.g. by relation_type or direction).

Result: Knowledge can be populated from URLs/PDFs/imports; one relation model supports both node-based (flow) and view-based (parents–children) navigation; Articles are linked to topics and entities.

---

## Use case 4: Track money flow, reports, and accounting documents

**Goal:** Track money flow and produce reports and accounting documents (statements, cash flow, bank movements).

### Current state

| Area           | Existing                                                                                                                             | Missing                                                                                                                                                                                   |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Money**      | [apps/money/models.py](../apps/money/models.py): **MoneyCategory**, **Transaction** (amount, kind, date, category, counterparty, note). | **Budget**: no model. **Transaction ↔ Product / Deadline**: no FKs; no link to projects or invoice-like deadlines.                                                                        |
| **Accounting** | [apps/accounting/models.py](../apps/accounting/models.py): **JournalEntry**, **JournalEntryLine** (account_code, debit, credit).        | **Bank**: no BankAccount or BankMovement. **Link to Money**: no FK from JournalEntry/Line to Transaction. **Reports**: no model for generated reports (e.g. P&L, cash flow) or templates. |


### Recommended changes (use case 4)

- **Money**
  - Add optional **FKs on Transaction**: `product`, `deadline` (for "invoice paid" or "expense for this project"), to support project-level and deadline-linked reporting.
  - Add **Budget** model: e.g. category (or product), period (month/year), amount, optional alert thresholds; used for "track spend vs budget" and reports.
- **Accounting**
  - Add **BankAccount**: name, identifier, tenant; and **BankMovement**: account FK, date, amount, label, optional FK to Transaction (reconciliation).
  - Add **link from journal to Money**: optional FK on **JournalEntry** (or on a line) to **Transaction** (or a batch) so entries can be traced to Money; supports "input from Money" and audit.
  - **Reports**: add **Report** (or **GeneratedReport**): report_type (e.g. P&L, balance_sheet, cash_flow), period, generated_at, file/store reference or JSON; optional template/config. Alternatively keep reports as "on-demand only" and add only report_type + period in API; add stored reports later if needed.

Result: Money supports project/deadline linkage and budgets; Accounting has bank accounts and movements, links to Money, and a path to stored reports for accounting documents.

---

## Decided: Parts, ApiKey, and Credential (hybrid)

**Decision:** Keep **Part** and promote **ApiKey** and **Credential** to first-class models in the **parts** app. Part remains the generic traceable asset; ApiKey and Credential get their own models for rotation, scopes, and security workflows.

- **Part:** Covers Token, Account, License, Other. Same attachment to System/Product (generic FK). Add optional **expires_at** for tokens/licenses. No rotation fields on Part.
- **ApiKey:** First-class model with name, description, value_masked, **last_rotated_at**, **next_rotation_due**, optional scope/environment, parent (System/Product). Dedicated list/detail and actions (e.g. "Rotate", "Set next rotation").
- **Credential:** First-class model with the same attachment pattern and rotation fields as ApiKey; type-specific validation and UI.
- **Unified UI:** Dedicated "API Keys" and "Credentials" sections; one **"Parts & keys"** (or "Assets") aggregate view per Product/System that combines Part + ApiKey + Credential so "everything attached to this project" stays in one place.
- **Deadlines:** Link to any expirable or rotatable entity via a **generic relation** (ContentType + object_id) to Part, ApiKey, Credential, or ServiceCredential. Rotation dates live on ApiKey and Credential (and ServiceCredential in Services); Part has optional expiry only.

---

## Summary: what to add or extend

| App                            | Add or extend                                                                                                                                       |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **products**                   | M2M to Plan; optional M2M to System; optional M2M to Milestone.                                                                                     |
| **plans**                      | No new fields; relation from Product side.                                                                                                            |
| **milestones**                 | Optional M2M or FK from Product for "project milestones."                                                                                             |
| **tasks**                      | Optional FKs (or generic): product, plan, milestone.                                                                                                  |
| **integrations**               | New model: Integration (type, ExternalService, optional Product).                                                                                     |
| **systems**                    | M2M to Product ("used by").                                                                                                                           |
| **parts**                      | First-class **ApiKey** and **Credential** with rotation dates, scope; Part keeps Token/Account/License/Other, optional **expires_at**.              |
| **knowledge**                  | KnowledgeSource; KnowledgeRelation (generic source/target); Article M2M to Topics + link to entities.                                                 |
| **deadlines**                  | Generic relation (ContentType + object_id) to Part, ApiKey, Credential, or ServiceCredential for expiring/rotation-due.                              |
| **services**                   | On ServiceCredential: `last_rotated_at`, `next_rotation_due`.                                                                                        |
| **money**                      | Transaction: optional product, deadline; new Budget model.                                                                                          |
| **accounting**                 | BankAccount, BankMovement; link JournalEntry/line to Transaction; optional Report (or on-demand only).                                                |
| **checks** (new app, optional) | PlannedCheck (type, schedule, last/next run, result, Product/System).                                                                                |

---

## Suggested implementation order

1. **Use case 1 (tracking):** Product–Plan–Task–System–Integrations–Knowledge links so "project" view has all data.
2. **Use case 2 (security):** Introduce first-class **ApiKey** and **Credential** with rotation fields; add optional **expires_at** on Part; add **last_rotated_at** / **next_rotation_due** on ServiceCredential; add **Deadline** generic relation to Part/ApiKey/Credential/ServiceCredential; then add checks app and PlannedCheck if planned checks are in scope.
3. **Use case 3 (knowledge):** KnowledgeSource and KnowledgeRelation; Article↔Topics and entities; then ingestion and UI (flow + parent–child).
4. **Use case 4 (money):** Transaction links and Budget; then BankAccount/BankMovement and report generation/linking.

This keeps the existing app boundaries, avoids redundant "projects" app usage (Products = projects), and adds only the models and relations needed to satisfy the four use cases. The Parts/ApiKey/Credential hybrid is decided and reflected in [operational_project_plan.md](operational_project_plan.md).
