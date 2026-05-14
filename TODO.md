# TODO — Frontend ↔ Live FastAPI Integration

## Phase 1 — Frontend analysis (already done)
- [x] Inspect auth pages, Zustand auth store, AuthGuard
- [x] Inspect API layer and sockets layer
- [x] Identify remaining mock usage in stores/components
- [x] Document endpoint mapping gaps

## Phase 2 — Environment setup
- [x] Update `frontend/.env.local` to use `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL`
- [x] Update `frontend/src/lib/api/config.ts` to read `NEXT_PUBLIC_API_URL`
- [x] Update `frontend/src/services/socket.tsx` to read `NEXT_PUBLIC_WS_URL`


## Phase 3 — API client
- [x] Create/update `frontend/src/lib/api/client.ts` (token injection, refresh + retry, clear tokens + redirect)
- [x] Add token helper functions (get/set/clear access+refresh)


## Phase 4 — Auth integration
- [ ] Update `frontend/src/store/authStore.ts` to save backend user/role (no hardcoded role)
- [ ] Wire auth flows to use centralized client refresh behavior
- [ ] Ensure logout clears storage + redirects

## Phase 5 — Service layer replacement
- [ ] Replace elder/family/caregiver stores data sources with live API modules
- [ ] Implement any missing frontend API services (tenant/rbac/telemetry/chat) based on backend

## Phase 6 — Dashboard integration
- [ ] Swap widget data sources to store-backed real data (preserve UI)
- [ ] Validate role-based dashboards

## Phase 7 — WebSockets
- [ ] Authenticate socket connections and map backend events:
  - [ ] alert:new
  - [ ] telemetry:update
  - [ ] chat:message
- [ ] Implement reconnection/backoff

## Phase 8 — End-to-end testing
- [ ] Run `npm install`
- [ ] Run `npm run lint`
- [ ] Run `npm run typecheck`
- [ ] Run `npm run build`
- [ ] Manual browser tests (login/register, protected routes, CRUD actions, DB verification, logout, refresh test)

## Phase 9 — Database verification
- [ ] Verify PostgreSQL tables after each key frontend action

## Phase 10 — Documentation
- [ ] Create `FRONTEND_BACKEND_INTEGRATION.md`
- [ ] Update `MIGRATION_PROGRESS.md`
- [ ] Update `README.md` if needed

## Phase 11 — Git commit
- [ ] Commit with message: `feat(frontend): integrate live FastAPI backend and PostgreSQL`

