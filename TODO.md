# TODO

## RBAC + Swagger authorization fixes
- [ ] Update `backend/app/dependencies/authorization.py` with required debug logs and improved 401/403/404 mapping.
- [ ] Update `backend/app/api/v1/rbac.py` to ensure Swagger/OpenAPI security is correctly declared and logged.
- [ ] Add idempotent RBAC seeding helper (`backend/app/services/rbac_seeding.py`).
- [ ] Hook seed+default role assignment during user registration (`backend/app/api/v1/auth.py` or `backend/app/services/auth_service.py`).
- [ ] Run backend tests related to RBAC/auth.

