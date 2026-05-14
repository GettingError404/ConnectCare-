# ConnectedCare+ Frontend (Next.js 15)

ConnectedCare+ is a preservation-first migration of the original Loveable-generated frontend to Next.js 15 App Router.

## Architecture Overview

- Framework: Next.js 15 (App Router)
- Language: TypeScript (strict mode)
- Styling: Tailwind CSS + shadcn/ui
- State: Zustand stores in `src/store`
- Data fetching: TanStack Query
- Forms/validation: React Hook Form + Zod
- Charts: Recharts
- Motion/icons: Framer Motion + Lucide React
- i18n foundation: next-intl provider wiring with message bundles in `src/messages`
- PWA: next-pwa (service worker + offline fallback)

## Project Structure

- App routes: `src/app/**`
- Reusable components: `src/components/**`
- Stores: `src/store/**`
- Mock data: `src/data/**`
- Messages: `src/messages/**`

Note: Three preserved legacy dashboard implementations are still used as compatibility wrappers:

- `src/pages_legacy/ElderDashboard.tsx`
- `src/pages_legacy/FamilyDashboard.tsx`
- `src/pages_legacy/CaregiverDashboard.tsx`

## Development Commands

- Install deps: `npm install`
- Run dev server: `npm run dev -- --hostname 0.0.0.0 --port 3000`
- Lint: `npm run lint`
- Typecheck: `npm run typecheck`
- Production build: `npm run build`
- Start production server: `npm run start`

## Verification Status

Current verification pass confirms:

- Next.js production build succeeds
- TypeScript typecheck succeeds
- Lint succeeds (warnings only)
- Dev server starts successfully
- Core route navigation works across family/elder/caregiver/admin surfaces
- Charts and responsive navigation render correctly in smoke testing
- Hydration mismatch issues in protected routes were fixed

## Backend Integration Notes

- Auth routes are wired to the live backend profile and token endpoints.
- Dashboard stores hydrate from live backend services instead of the old static mock seeds.
- The backend currently requires a tenant id for healthcare and telemetry requests.
- The websocket client now uses the browser `WebSocket` API, but the backend websocket route still needs to be mounted in the running app.
- Manual verification showed the family and caregiver shells render successfully, while live telemetry hydration remains blocked until tenant-bearing JWTs are available.

## Migration Notes

- Legacy Vite/React Router entry artifacts were removed (`vite.config.ts`, `index.html`, `src/main.tsx`, `src/App.tsx`, and obsolete router-only pages/components).
- Obsolete Vite dependencies were removed.
- The app now runs exclusively through Next.js scripts.
