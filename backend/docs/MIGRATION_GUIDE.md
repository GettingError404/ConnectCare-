# Migration Guide — Alembic

STATUS: IMPLEMENTED
Last verified against repository state: 2026-05-09

Purpose

Explain how to create, review, and apply migrations safely for this codebase (with Timescale hypertables).

Workflow

1. Update SQLAlchemy model(s) under `app/models/`.
2. Create a new autogenerate revision:

```bash
alembic revision --autogenerate -m "describe change"
```

3. Edit the migration file in `alembic/versions/`:
   - Ensure columns referenced by `create_hypertable` exist (commonly `recorded_at`).
   - Keep migrations idempotent where possible; downgrade steps should tolerate missing indexes/objects.
   - Avoid optional Timescale-specific policy code unless you maintain it across environments.

4. Run migrations locally first:

```bash
alembic upgrade head
```

5. Smoke test the app (OpenAPI generation, sample ingest, metrics) before promoting to staging.

Current migration set (verified):

- `20260506_1609_10911737759d_initial_schema.py`
- `20260506_1705_add_password_hash_and_device_name.py`
- `20260506_1900_20260506a2_create_alerts.py`
- `20260508_1100_add_tenants.py`
- `20260508_1130_add_users_tenant_id.py`
- `20260508_1200_add_rbac_tables.py`
- `20260508_1210_seed_rbac_permissions_roles.py`
- `20260508_1300_add_healthcare.py`
- `20260508_1310_update_devices.py`
- `20260508_1320_add_streams.py`
- `20260508_1330_add_alerts.py`
- `20260508_2000_add_auth_sessions.py`
- `20260508_2100_add_ai_memory_persistence.py`

Timescale specifics

- Use `create_hypertable('device_telemetry', 'recorded_at')` in a migration only if `recorded_at` exists and appropriate PK/index strategy is used.
- Hypertable creation is a one-time operation — avoid attempting to recreate.

Rollback guidance

- Downgrades may not always be able to drop hypertables cleanly; plan forward-only migrations where necessary.
- Keep migration history compact and deterministic; avoid many tiny follow-up migrations that change the same table repeatedly.

Why this document matters

Migrations are the main risk surface for DB ops; this guide consolidates learnings discovered during prior refactors (hypertable creation and downgrade idempotency).

Which modules this documents

- `alembic/versions/*`, `app/models/*`.

## Limitations

- Some older docs still refer to Timescale behavior generically rather than by actual migration file.

## Future Work

- Document any new migration only after it exists in `alembic/versions/`.
