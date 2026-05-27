# Architecture module

**Purpose:** Registry-first software architecture per **project**: environments, infrastructure components (database, broker, load balancer, …), and connections between them.

**App:** `apps.architecture` (tenant schema)

## Models

- **ArchitectureProfile** — FK `project`; environment (prod/staging/dev); `is_primary`
- **ArchitectureComponent** — typed component (`database`, `message_broker`, `load_balancer`, …); optional FK `system`; vendor/engine; host/port/region; `metadata` JSON
- **ArchitectureConnection** — `source` / `target` components; `connection_type` (depends_on, routes_to, reads_from, …)

Diagram UI is optional later; v1 is admin CRUD lists.

See [project management plan](../../.cursor/plans/project_management_features_10041c5f.plan.md).
