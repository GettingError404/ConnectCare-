# Authentication & Authorization — ConnectedCare+

STATUS: IMPLEMENTED
Last verified against repository state: 2026-05-09

Purpose

Document the JWT-based authentication, refresh token rotation, and RBAC flow implemented in the codebase and how to extend it safely.

## Authentication Flow

### Token Components
- **Access Token** (JWT): Short-lived (default 60 minutes), contains user_id, tenant_id, roles
- **Refresh Token** (JWT): Long-lived (default 30 days), opaque jti (unique ID) + family_id (for reuse attack detection)
- **User Session** (`UserSession` model): Tracks device_info, ip_address, user_agent, created_at for session management
- **Refresh Token Record** (`RefreshToken` model): Persists jti, family_id, user_id, session_id, revoked flag, expires_at

### Token Creation (`app.services.auth_service.create_token_pair()`)
1. Create session in `user_sessions` table via `SessionRepository.create_session()`
2. Generate access token: payload = {user_id, tenant_id, roles}, expire = 60 min
3. Generate refresh token: payload = {user_id, tenant_id, roles, jti (unique), family_id (for rotation tracking)}, expire = 30 days
4. Persist refresh token record to `refresh_tokens` table with jti, family_id, expires_at, revoked=False
5. Return {"access_token", "refresh_token", "token_type": "bearer"}

### Token Validation
- `app.core.security.get_current_user()` dependency
  - Extracts token from Authorization header (OAuth2PasswordBearer scheme)
  - Decodes JWT using `SECRET_KEY` and `ALGORITHM` (HS256 by default)
  - Validates exp, iat claims
  - Looks up User by user_id from token payload
  - Raises HTTPException(401) if invalid

### Refresh Token Rotation (`app.services.auth_service.rotate_refresh_token()`)
- Client sends old refresh_token_str
- Decode and extract jti, family_id, user_id
- Look up RefreshToken record in DB by jti
- If revoked or missing: revoke entire family (reuse attack detection) → HTTPException(401)
- Otherwise: issue new token pair (new jti, same family_id)
- Mark old jti as revoked
- Return new {"access_token", "refresh_token"}

### Password Management
- Passwords hashed using **passlib with pbkdf2_sha256** scheme (not plaintext)
- `get_password_hash(plain_password)` → hashed via pwd_context
- `verify_password(plain_password, hashed_password)` → timing-safe comparison
- User registration: `create_user()` hashes password, checks for duplicate email
- Login: `authenticate_user()` verifies email + password, returns User on success

## Authorization (RBAC)

### Models
- `Permission` — fine-grained action definitions (e.g., "users:read", "alerts:write")
- `Role` — named role collections of permissions
- `RolePermission` — many-to-many join (role ↔ permission)
- `UserRole` — many-to-many join (user ↔ role)

### Authorization Checks
- Dependencies in `app.dependencies.authorization`
  - `require_permission(permission_slug)` — returns dependency that validates user has permission
  - `require_role(role_slug)` — returns dependency that validates user has role
  - Both extract tenant_id via `require_tenant_context` and call `RBACService.check_*()` methods
- `RBACService` (`app.services.rbac`) — business logic for permission/role checks
- `RBACRepository` (`app.repositories.rbac`) — thin data access (queries roles, permissions, user_roles)

### Usage in Routes
```python
from app.dependencies.authorization import require_permission, require_role

@router.delete("/elder/{elder_id}")
async def delete_elder(
    elder_id: str,
    user=Depends(require_permission("elders:delete"))
):
    # only users with "elders:delete" permission reach here
    ...

@router.post("/admin/roles")
async def create_role(
    payload: CreateRoleRequest,
    user=Depends(require_role("admin"))
):
    # only users with "admin" role reach here
    ...
```

### RBAC Failure Logging
- Authorization failures logged via `app.dependencies.authorization` with structured logs
- Includes: permission/role required, tenant_id, user_id, action attempted
- Failures return HTTPException(403 Forbidden) with "Insufficient permissions" detail

## Multi-Tenant Isolation

### Tenant Context Extraction
- `TenantContextMiddleware` (`app.middleware.tenant_context`) runs early in middleware stack
- Extracts token from Authorization header, decodes JWT
- Reads tenant_id from token payload
- Attaches tenant_id to `request.state.tenant_id` for downstream use
- All route handlers must use this tenant_id to filter queries (mandatory, no cross-tenant queries)

### Tenant Validation
- User's tenant_id (from token) must match resource's tenant_id before allow access
- Repository methods require tenant_id parameter (enforced, no "tenant-less" queries)
- RBAC checks validate user belongs to tenant and has required permission within tenant

## Configuration

### Environment Variables
```bash
SECRET_KEY=<your-secret-key-min-32-chars>  # For JWT signing
ALGORITHM=HS256                              # JWT algorithm (default: HS256)
ACCESS_TOKEN_EXPIRE_MINUTES=60              # Access token TTL (default: 60)
REFRESH_TOKEN_EXPIRE_DAYS=30                # Refresh token TTL (default: 30)
```

## Why This Document Matters

Authentication and authorization are security-critical. This document tells maintainers:
- Exact modules to use for token generation, validation, and rotation
- How refresh token reuse attacks are prevented
- Where to add new protected endpoints
- How tenant isolation is enforced

## Which Modules This Documents

- **Token management:** `app.core.security` (creation, validation, hashing), `app.services.auth_service` (token pair, refresh rotation)
- **Models:** `app.models.auth` (UserSession, RefreshToken), `app.models.user` (User), `app.models.rbac` (Permission, Role, UserRole, RolePermission)
- **Data access:** `app.repositories.auth` (SessionRepository, RefreshTokenRepository), `app.repositories.rbac`
- **Authorization:** `app.dependencies.authorization`, `app.services.rbac` (RBACService)
- **Routes:** `app.api.v1.auth` (login, register, refresh), plus all routes using require_permission/require_role
- **Middleware:** `app.middleware.tenant_context` (tenant extraction)
