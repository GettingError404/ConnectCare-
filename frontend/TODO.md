# Migration TODO - ConnectedCare+

## Phase 1 — Compatibility fixes (preserve UI)
- [ ] Audit which routes/pages are actually rendered by `src/app/*` vs `src/pages_legacy/*`.
- [x] Remove `react-router-dom` dependency from any component used by App Router (fix `src/components/NavLink.tsx`).


- [ ] Ensure login/register flows still work under App Router routes.

## Phase 2 — Internationalization (next-intl)
- [ ] Implement locale wiring for next-intl based on existing language selection behavior.
- [ ] Ensure all existing translation keys/messages remain unchanged.
- [ ] Ensure Language Switcher component (if present) updates locale without changing layout.

## Phase 3 — TypeScript strict hardening
- [ ] Convert/verify any JS/JSX remnants; ensure strict no implicit any.
- [ ] Fix TS errors without changing runtime behavior.

## Phase 4 — Folder reorganization (required structure)
- [ ] Move files into the required `src/app, components, features, hooks, lib, services, store, types, messages, styles` folders.
- [ ] Update import paths accordingly; do not change component APIs.

## Phase 5 — State management
- [ ] Ensure all app state uses Zustand where appropriate; preserve behavior.

## Phase 6 — Data fetching
- [ ] Introduce/confirm TanStack Query hooks/services used by pages while preserving mock behavior.

## Phase 7 — Forms
- [ ] Ensure React Hook Form + Zod wiring matches existing validations.

## Phase 8 — Real-time
- [ ] Verify Socket.IO provider lifecycle and typed events; preserve existing updates.

## Phase 9 — PWA
- [ ] Verify next-pwa config and offline fallbacks match existing UX.

## Phase 10 — Verification
- [ ] Run `npm run typecheck`.
- [ ] Run `npm run lint`.
- [ ] Run `npm run build`.
- [ ] Run Playwright tests (if available) to validate routes and key interactions.

