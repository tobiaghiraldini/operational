# Tenant user permissions

Operational uses [django-tenant-users](https://github.com/Corvia/django-tenant-users): one **TenantUser** in the public schema, and a **UserTenantPermissions** row per tenant schema.

## Why public `UserTenantPermissions` admin does not fix tenant access

On `localhost:8000` (public schema), `/admin/permissions/usertenantpermissions/<id>/change/` edits:

- A row in **public** `permissions_usertenantpermissions`
- M2M links to **public** `auth_permission` rows

When a user logs into a **customer tenant** admin, Django checks:

- `UserTenantPermissions` in **that tenant's schema**
- `auth_permission` primary keys from **that schema**

Assigning `projects.view_project` on public does nothing for tenant admin, because that codename either does not exist on public or has a different PK than in the tenant schema.

## Correct ways to grant tenant permissions

### 1. TenantUser admin (recommended)

Use the **public** admin (`localhost:8000`), not a customer tenant domain.

| Task | URL / navigation |
|------|------------------|
| Tenant membership | `/admin/users/tenantuser/<id>/change/` → **Tenant access** |
| Model permissions | `/admin/users/tenantuser/<id>/tenant-permissions/` or change form → **Manage tenant permissions** (top action button) |

Steps:

1. Public admin → **Users** (sidebar) → open user
2. **Manage tenant permissions** (button at top of change form, or **Permissions** column on the list)
3. Choose tenant → **Apply default business permissions** or edit the permission list
4. Save

**Do not** use **Public schema permissions** (`/admin/permissions/usertenantpermissions/`) for projects, money, etc. That screen only affects the public schema.

Membership save (**Tenant access** fieldset) also runs `ensure_tenant_membership`, which grants default permissions for apps in `DefaultBusinessPermissionsPolicy.APP_LABELS`.

Every user always belongs to the **public** tenant (for platform login). That membership is not shown in the tenant picker and cannot be removed; only customer tenants are listed there.

### 2. Management commands

Re-apply defaults for all staff in all tenants:

```bash
python manage.py sync_default_business_permissions
```

Grant/revoke specific codenames for one user:

```bash
python manage.py grant_tenant_user_permissions \
  --schema=your_tenant \
  --email=user@example.com \
  --apply-defaults

python manage.py grant_tenant_user_permissions \
  --schema=your_tenant \
  --email=user@example.com \
  --grant=projects.view_project,issues.view_issue

python manage.py grant_tenant_user_permissions \
  --schema=your_tenant \
  --email=user@example.com \
  --revoke=projects.delete_project
```

### 3. After new apps or models ship

1. Add the app label to `APP_LABELS` in [`apps/users/services/default_business_permissions_policy.py`](../../apps/users/services/default_business_permissions_policy.py)
2. `python manage.py migrate_schemas`
3. `python manage.py sync_default_business_permissions`

## Requirements for tenant admin module access

| Flag | Effect |
|------|--------|
| `is_staff=True` on **tenant** row | Required for admin login |
| `is_superuser=True` | Bypasses all permission checks |
| Staff + model permissions | `view_*`, `add_*`, `change_*`, `delete_*` per model |

Default policy grants all permissions for whitelisted app labels to **staff, non-superuser** rows only.

## Cache

Permission checks cache `tenant_perms` per schema on the user. After changing permissions, re-login or save the user via TenantUser admin (cache is cleared automatically).

## Related code

- Policy: [`apps/users/services/default_business_permissions_policy.py`](../../apps/users/services/default_business_permissions_policy.py)
- Helpers: [`apps/users/services/tenant_permissions_admin.py`](../../apps/users/services/tenant_permissions_admin.py)
- Admin: [`apps/users/admin.py`](../../apps/users/admin.py)
