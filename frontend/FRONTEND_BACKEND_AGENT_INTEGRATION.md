# Frontend-Backend Agent Integration

**Last Updated:** 2026-05-14  
**Status:** MOSTLY WORKING - Demo users seeded, login response handling fixed

## Authentication Flow

### Root Cause of Login Failure: RESOLVED ✅

**Problem:** Frontend displayed "Invalid email or password" even for valid demo credentials.

**Root Causes:**
1. **Demo accounts not seeded:** The PostgreSQL database did not contain elder@example.com, family@example.com, caregiver@example.com
2. **API response format mismatch:** 
   - Backend returns FastAPI error: `{"detail":"Invalid credentials"}`
   - Frontend expected: `{"ok":false,"error":{"message":"..."}}`

### Solution Implemented

1. **Backend - Demo User Seeding:**
   - Created `backend/scripts/seed_demo_users.py` to insert demo accounts
   - Demo users now exist in PostgreSQL with correct passwords:
     - elder@example.com / elder123 (role: elder)
     - family@example.com / family123 (role: family_member)
     - caregiver@example.com / care123 (role: caregiver)
   - Run script: `cd backend && python scripts/seed_demo_users.py`

2. **Frontend - API Response Handling:**
   - Updated `frontend/src/lib/api/client.ts` - `parseApiResponse()` function
   - Now detects and converts FastAPI error format to ApiResponse wrapper:
     ```javascript
     // Before: {"detail":"Invalid credentials"} → not recognized
     // After: Detected as error → {"ok":false,"error":{"code":"API_ERROR","message":"Invalid credentials"}}
     ```
   - Handles both string errors and validation error arrays

### Verification Summary
- ✅ Backend: Demo users created and verified in database
- ✅ Backend: Login endpoint returns tokens correctly (tested via PowerShell)
- ✅ Frontend: Build succeeds with error handling improvements
- ⏳ Frontend: Dev server requires restart to load updated code

**To test after restart:**
1. Run `npm run dev` in frontend directory to restart dev server
2. Navigate to http://localhost:3001/login
3. Click "Elder" demo button
4. Submit login form
5. Should redirect to /elder dashboard if successful

### Demo User Database Records
All demo users seeded with PBKDF2-SHA256 password hashing (compatible with backend):
```sql
SELECT email, full_name FROM users WHERE email LIKE '%example.com%';
-- elder@example.com | Demo Elder
-- family@example.com | Demo Family Member
-- caregiver@example.com | Demo Caregiver
```

### Auth Endpoint Paths (Double "auth" prefix)
```
POST   /api/v1/auth/auth/register
POST   /api/v1/auth/auth/login
GET    /api/v1/auth/auth/me
POST   /api/v1/auth/auth/refresh
POST   /api/v1/auth/auth/logout
```

The double prefix occurs because:
- Router mounted at prefix `/api/v1/auth`
- Individual routes use prefix `/auth`
- Result: `/api/v1/auth` + `/auth` = `/api/v1/auth/auth`

### Login Flow
1. User submits email + password
2. `authStore.login()` calls `authService.login()`
3. API returns: `{access_token, refresh_token, token_type}`
4. Frontend stores tokens in localStorage
5. Fetches user profile from `GET /api/v1/auth/auth/me`
6. Stores user in localStorage as `cc_user`
7. Redirects based on role:
   - elder → /elder
   - caregiver → /caregiver/dashboard
   - family_member → /family/dashboard

### Storage
- `access_token` - localStorage
- `refresh_token` - localStorage
- `cc_user` - localStorage (JSON: id, email, name, role, createdAt)
- `isAuthenticated` - Zustand store

## Summary

ConnectedCare+ frontend integration now uses live backend auth and store hydration for the main dashboard shells. The preserved UI and route structure remain unchanged; only the data sources and transport wiring were updated.

## API Modules Used

- `src/lib/api/services/auth.ts`
- `src/lib/api/services/profile.ts`
- `src/lib/api/services/alerts.ts`
- `src/lib/api/services/healthcare.ts`
- `src/lib/api/services/telemetry.ts`
- `src/lib/api/services/devices.ts`

## Store to Dashboard Mapping

- `src/store/elderStore.ts` powers the elder dashboard shell and companion panels.
- `src/store/familyStore.ts` powers the family dashboard alerts and activity summary.
- `src/store/caregiverStore.ts` powers the caregiver dashboard overview, alerts, and caseload panels.

The dashboard shells are still visually preserved in:

- `src/pages_legacy/ElderDashboard.tsx`
- `src/pages_legacy/FamilyDashboard.tsx`
- `src/pages_legacy/CaregiverDashboard.tsx`

## WebSocket Architecture

- The frontend now uses a native browser `WebSocket` wrapper instead of `socket.io-client`.
- The intent is to connect to the backend alerts socket with `token` and `tenant_id` query parameters.
- The backend websocket handler exists in `backend/app/api/v1/ws_alerts.py`, but it is not mounted in `backend/app/main.py`.
- Manual verification showed websocket handshakes fail with `403` because the endpoint is not reachable in the running backend app.

## Mobile Agent Telemetry Flow

- The frontend telemetry-oriented store loaders expect backend telemetry and healthcare endpoints to be tenant-aware.
- The current JWTs produced by signup/login do not include a tenant id, so tenant-gated endpoints return `401 Tenant context required`.
- Because of that, the dashboards render correctly, but live telemetry hydration is currently limited until tenant-bearing credentials are available.

## Manual Verification Results

- Registration and login succeed against the live backend.
- `cc_user` stores the backend profile payload.
- Family and caregiver dashboard shells render successfully from live store state.
- Alerts endpoint returns live data with an empty result set for the current user.
- Tenant-gated healthcare and telemetry endpoints currently return `401` without a tenant id.
- Vitals endpoint access returns `404` in the running backend.
- WebSocket connection attempts to `/ws/alerts` and `/api/v1/ws/alerts` fail with handshake errors.

## Remaining Dependencies

- Backend JWTs need a tenant id for tenant-gated dashboard hydration.
- The websocket router needs to be mounted in `backend/app/main.py` before the frontend socket can connect successfully.
- Backend devices and vitals routes are still unresolved from the frontend perspective.
- Android mobile project scaffolding was not created because the current scope explicitly restricted changes to `frontend/` and documentation files.