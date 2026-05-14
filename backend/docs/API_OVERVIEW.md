# API Overview — ConnectedCare+

STATUS: IMPLEMENTED
Last verified against repository state: 2026-05-09

Purpose

Map the public API surface actually registered in `app/main.py` and the route definitions in `app/api/v1/*.py`.

## Actual Route Registration

`app/main.py` includes routers with additional prefixes, so the currently exposed paths are the combination of the main prefix and each router's own prefix.

## Implemented Routers

| Router file | Router prefix in file | Main registration prefix | Example exposed path |
|---|---|---|---|
| `app/api/v1/auth.py` | `/auth` | `/api/v1/auth` | `/api/v1/auth/auth/login` |
| `app/api/v1/tenants.py` | `/v1` | `/api/v1/tenants` | `/api/v1/tenants/v1/tenants` |
| `app/api/v1/rbac.py` | `/v1` | `/api/v1/rbac` | `/api/v1/rbac/v1/permissions` |
| `app/api/v1/healthcare.py` | `/api/v1/healthcare` | `/api/v1/healthcare` | `/api/v1/healthcare/api/v1/healthcare/elders/{elder_id}` |
| `app/api/v1/telemetry.py` | `/api/v1/telemetry` | `/api/v1/telemetry` | `/api/v1/telemetry/api/v1/telemetry/elders/{elder_id}/latest` |
| `app/api/v1/alerts.py` | `/api/v1/alerts` and `/alerts` | `/api/v1/alerts` | `/api/v1/alerts/api/v1/alerts/rules` |

## Actual Endpoints

- `POST /api/v1/auth/auth/register` — create user
- `POST /api/v1/auth/auth/login` — issue access and refresh token pair
- `POST /api/v1/auth/auth/refresh` — rotate refresh token
- `POST /api/v1/auth/auth/logout` — revoke refresh token
- `POST /api/v1/auth/auth/logout_all` — revoke all sessions for current user
- `GET /api/v1/tenants/v1/tenants` — list tenants
- `POST /api/v1/tenants/v1/tenants` — create tenant
- `GET /api/v1/tenants/v1/organizations` — list organizations in current tenant
- `POST /api/v1/rbac/v1/roles` — create role
- `GET /api/v1/rbac/v1/permissions` — list permissions
- `POST /api/v1/healthcare/api/v1/healthcare/elders` — create elder
- `GET /api/v1/healthcare/api/v1/healthcare/elders/{elder_id}` — get elder
- `GET /api/v1/telemetry/api/v1/telemetry/elders/{elder_id}/latest` — latest telemetry for elder
- `GET /api/v1/alerts/api/v1/alerts/rules` — list alert rules
- `GET /api/v1/alerts/api/v1/alerts/events/active` — list active alerts
- `GET /alerts/me` — current user's alert list (legacy router in same file)
- `POST /devices/register` — device registration
- `GET /devices/me` — list user's devices
- `POST /v1/vitals` — create health vital
- `GET /v1/vitals/{user_id}` — get user's vitals
- `WS /ws/alerts?token=...&tenant_id=...` — websocket alert subscription

## Authentication

- Most endpoints expect a JWT Bearer token. Use `Authorization: Bearer <token>` header.
- Tenant-aware routes use `TenantContextMiddleware` and `require_tenant_context()` for tenant isolation.
- Permission enforcement is performed with dependencies from `app.dependencies.authorization`.

## API Docs

- FastAPI OpenAPI is available via `/openapi.json`.
- Interactive docs are available via `/docs`.

## Limitations

- Router prefixes are inconsistent across files, so some registered paths are nested more deeply than intended.
- No separate API versioning strategy exists beyond the current `app.main` registrations.

## Future Work

- Normalize router prefixes only if the codebase is intentionally refactored.

## Which Modules This Documents

- `app/api/v1/*`, `app/schemas/*`, `app/dependencies/authorization.py`, `app/middleware/tenant_context.py`, `app/main.py`
