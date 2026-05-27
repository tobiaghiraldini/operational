# Architecture scaffold

Summary of the scaffolded apps and high-level architecture (see [operational_project_plan.md](../plans/operational_project_plan.md)).

## Apps and placement

### Shared schema (SHARED_APPS)

| App | Role | Models |
|-----|------|--------|
| `apps.tenants` | Tenant registry, Tenant, Domain | Tenant, Domain |
| `apps.subscriptions` | Subscription tiers | SubscriptionTier |
| `apps.core` | Shared code, utils, orchestration | (none) |
| `apps.ai` | AI / MCP (future) | (none) |
| `apps.api` | REST API entrypoint | (none) |
| `apps.integrations` | External API clients (Stripe, etc.) | (none) |

### Tenant schema (TENANT_APPS)

| App | Role | Models |
|-----|------|--------|
| `apps.projects` | **Project management** hub (plans, systems, architecture) | Project |
| `apps.architecture` | Architecture profiles & components per project | ArchitectureProfile, ArchitectureComponent, ArchitectureConnection |
| `apps.stack` | Technology registry (libs, frameworks) | Technology, TechnologyUsage |
| `apps.issues` | Lightweight issues | Issue |
| `apps.testing` | Test scenarios & runs | TestScenario, TestRun |
| `apps.operations` | Live operational snapshots | OperationalSnapshot |
| `apps.checks` | Planned security/ops checks | PlannedCheck |
| `apps.solutions` | ADR-style solutions | Solution |
| `apps.services` | External service registry, credentials | ExternalService, ServiceCredential |
| `apps.dashboard` | Per-user widgets | DashboardWidget |
| `apps.plans` | Plans (containers for milestones) | Plan |
| `apps.milestones` | Milestones (goals with dates) | Milestone |
| `apps.products` | **Commercial** products & licenses (SaaS, templates, IDEs) | Product, ProductLicense (planned reshape) |
| `apps.systems` | Reusable systems | System |
| `apps.parts` | Tokens, keys, credentials (generic FK to System/Product) | Part |
| `apps.topics` | Topics (tagging) | Topic |
| `apps.knowledge` | Knowledge articles | Article |
| `apps.tasks` | Tasks | Task |
| `apps.deadlines` | Deadlines | Deadline |
| `apps.money` | Categories, transactions | MoneyCategory, Transaction |
| `apps.accounting` | Journal entries | JournalEntry, JournalEntryLine |

## URL layout

- `/admin/` — Unfold admin (tenant-aware).
- `/api/` — API root (JSON with links and tenant name when on tenant).
- `/` — Homepage (index.html).

## Key model relations (to expand)

- **Milestone** → Plan (FK).
- **Part** → GenericForeignKey (**Project** or System; today incorrectly allows Product until migration).
- **Transaction** → MoneyCategory (FK).
- **JournalEntryLine** → JournalEntry (FK).
- **DashboardWidget** → User (FK).
- **ServiceCredential** → ExternalService (FK).

**Projects** ↔ Plans/Systems/Tasks; **Products** (commercial) ↔ ProductLicense, M2M Projects; Parts/Deadlines on Project/System. See [projects_module.md](../plans/projects_module.md) and [products_module.md](../plans/products_module.md).

**Tenant permissions:** See [tenant_permissions.md](tenant_permissions.md) — public vs tenant schema; use TenantUser → Manage tenant permissions, not public `UserTenantPermissions` M2M alone.

## Migrations

- Shared apps: applied to public schema.
- Tenant apps: applied to each tenant schema (django-tenants `migrate_schemas` or on tenant create).
- `django.contrib.contenttypes` and `django.contrib.auth` are listed in **both** `SHARED_APPS` and `TENANT_APPS` so tenant schemas have `django_content_type` and `auth_permission` (required by `parts`, `tenant_users.permissions`, and other tenant models).
- Tenant models reference the public-schema `TenantUser` via `TenantUserForeignKey` (`apps/core/db/tenant_user_foreign_key.py`) with `db_constraint=False` (django-tenant-users pattern).
- All migrations created and applied; `manage.py check` passes.
