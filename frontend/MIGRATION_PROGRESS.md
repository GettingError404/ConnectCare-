# Migration Progress

## Summary

Preservation-first frontend migration to Next.js 15 App Router has reached completion for Phase 1 and Phase 2 validation/cleanup.

## Completed Phases

### Phase 1 - Platform Migration

- Migrated scripts and runtime to Next.js 15
- Added App Router route structure under `src/app`
- Added provider composition in `src/app/providers.tsx`
- Added PWA setup (`next-pwa`) and offline fallback (`public/offline.html`)
- Added i18n message bundles (`src/messages/*.json`)
- Migrated auth guard flow for Next navigation
- Renamed `src/stores` to `src/store` and updated imports

### Phase 2 - Verification and Cleanup

- Verified route access and rendering across major screens
- Fixed protected-route hydration mismatch by delaying guard render until mount
- Removed obsolete Vite and React Router artifacts:
  - `vite.config.ts`
  - `index.html`
  - `src/main.tsx`
  - `src/App.tsx`
  - `src/vite-env.d.ts`
  - obsolete router-only legacy pages/components
- Removed obsolete dependencies (`vite`, `@vitejs/plugin-react`, `react-router-dom`)
- Validation suite status:
  - `npm run lint`: pass (warnings only)
  - `npm run typecheck`: pass
  - `npm run build`: pass
  - `npm run dev`: pass

## Current Architecture State

- Runtime is exclusively Next.js App Router
- Core dashboards remain visually preserved via compatibility wrappers to:
  - `src/pages_legacy/ElderDashboard.tsx`
  - `src/pages_legacy/FamilyDashboard.tsx`
  - `src/pages_legacy/CaregiverDashboard.tsx`

## Phase 9-11 Status

### Phase 9 - Manual Frontend <-> Backend Verification

- Verified auth registration and login against the live backend
- Confirmed `access_token` and `refresh_token` are stored in browser storage
- Confirmed `cc_user` is hydrated from the backend profile response
- Verified the family and caregiver dashboard shells render without crashing
- Verified live alerts fetch succeeds for the current user
- Verified tenant-gated healthcare and telemetry requests currently fail without a tenant id
- Verified websocket handshakes fail because the backend websocket route is not mounted in the running app

### Phase 10 - Documentation

- Added `FRONTEND_BACKEND_AGENT_INTEGRATION.md`
- Updated this migration log with the current integration status and remaining dependencies
- Updated the frontend README with live backend integration notes

### Phase 11 - Mobile Project Initialization

- Not started in this turn because the requested scope explicitly restricted changes to `frontend/` and documentation files
- Mobile scaffold remains a follow-up item if the scope restriction is relaxed

## Remaining Tasks

- Implement user-facing language switcher UI and route-based locale selection (i18n provider is wired, but switcher UI is not yet present)
- Gradually migrate remaining `src/pages_legacy/*` dashboard internals into fully route-native `src/app/**` components
- Optional hardening: address lint warnings (react-hooks dependency warnings and fast-refresh guidance)
- Resolve backend tenant-aware credential flow so healthcare and telemetry endpoints can hydrate live dashboard data
- Mount the backend websocket router before enabling live alert streaming

## Ready For Next Phase

Frontend is ready for the next integration pass once tenant-bearing auth and websocket routing are available.
