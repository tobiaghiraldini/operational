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
| `apps.projects` | Legacy projects | (empty) |
| `apps.services` | External service registry, credentials | ExternalService, ServiceCredential |
| `apps.dashboard` | Per-user widgets | DashboardWidget |
| `apps.plans` | Plans (containers for milestones) | Plan |
| `apps.milestones` | Milestones (goals with dates) | Milestone |
| `apps.products` | Products (live/dev/testing) | Product |
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
- **Part** → GenericForeignKey (System or Product).
- **Transaction** → MoneyCategory (FK).
- **JournalEntryLine** → JournalEntry (FK).
- **DashboardWidget** → User (FK).
- **ServiceCredential** → ExternalService (FK).

Plans ↔ Products, Products ↔ Systems, Tasks ↔ Products/Milestones, Deadlines ↔ Parts, etc. can be added in later iterations (generic relations or explicit FKs).

## Migrations

- Shared apps: applied to public schema.
- Tenant apps: applied to each tenant schema (django-tenants `migrate_schemas` or on tenant create).
- All migrations created and applied; `manage.py check` passes.
