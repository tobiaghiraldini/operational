# Parts module

**Purpose:** Traceable runtime assets on **projects** and **systems**: tokens, accounts, licenses; first-class **ApiKey** and **Credential** with rotation; aggregate via `parts_aggregate()`.

**App:** `apps.parts`

## Models

| Model | Parent (GFK) | Notes |
|-------|----------------|-------|
| **Part** | Project, System | token, account, license, other; optional `expires_at` |
| **ApiKey** | Project, System | `last_rotated_at`, `next_rotation_due`, scope, environment |
| **Credential** | Project, System | Same rotation fields; `credential_kind` |

Commercial vendor license keys live on **ProductLicense** (`apps.products`), not Part.

**Deadlines** link via generic FK to Part, ApiKey, Credential, or ServiceCredential.

See [operational_use_cases_vs_apps.md](operational_use_cases_vs_apps.md).
