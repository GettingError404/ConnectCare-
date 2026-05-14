# Database — ConnectedCare+

STATUS: IMPLEMENTED
Last verified against repository state: 2026-05-09

Purpose

Document the database design, Timescale usage, and migration workflow based on `app/models` and `alembic/`.

Primary database

- **PostgreSQL 14+** with **TimescaleDB** extension enabled for time-series telemetry
- **pgvector 0.4.2** extension enabled for vector similarity search (AI memory embeddings)
- Migrations are managed using **Alembic** (`alembic/versions`) with 13 deterministic revisions
- All tables have tenant isolation via `tenant_id` foreign key (mandatory in WHERE clauses)

Hypertable usage

- **`device_telemetry`** — time-series hypertable for device measurements (see `app/models/streams.py:DeviceTelemetry`)
  - Partitioned by `recorded_at` using Timescale hypertable in migration 20260508_1320
  - Primary key pattern: `id` (gen_random_uuid) + `recorded_at` (partition key)

Vector database (pgvector)

- **`ai_memory_embeddings`** — stores 1536-dimensional OpenAI embeddings for AI conversation chunks
  - Column: `embedding vector(1536)` using pgvector type
  - Index: IVFFlat cosine distance index (`idx_ai_memory_embeddings_vector_cosine`) for semantic search (similarity threshold queries)
  - Used for: retrieval-augmented generation (RAG) via cosine distance ranking
  - Idempotency: content_hash prevents duplicate embeddings, embedding_version tracks model changes

Domain tables (25 total)

**Multi-tenancy:**
- `tenants` — top-level tenant (organization)
- `organizations`, `organization_units` — hierarchical org structure within tenant (see `app/models/tenant.py`)
- `users` — tenant-scoped users with role assignments (see `app/models/user.py`)

**Authentication & Authorization:**
- `user_sessions` — active JWT sessions with expiration (see `app/models/auth.py`)
- `refresh_tokens` — refresh token storage for token rotation (see `app/models/auth.py`)
- `permissions` — fine-grained permission definitions (see `app/models/rbac.py`)
- `roles` — role definitions with permission bundles
- `role_permissions` — many-to-many mapping (role ↔ permission)
- `user_roles` — many-to-many mapping (user ↔ role)

**Device Telemetry & Streams:**
- `devices` — registered IoT/medical devices
- `vital_stream_events` — raw ingestion events with dedup metadata (see `app/models/streams.py`)
- `device_telemetry` — time-series measurements → Timescale hypertable (recorded_at partitioned)
- `vital_thresholds` — configurable thresholds for anomaly detection
- `vital_anomalies` — anomalies detected during telemetry evaluation
- `device_heartbeats` — periodic keep-alive signals from devices
- `ingestion_failure_logs` — failed ingest event records for debugging

**Alerting:**
- `alert_rules` — threshold-based alert rule definitions (see `app/models/alerts.py`)
- `alert_events` — generated alert instances (when rule fires)
- `alert_escalations` — alert escalation history and acknowledgements

**Healthcare:**
- `elders` — primary care recipients
- `caregivers` — care providers
- `doctors` — medical professionals
- `family_members` — family records
- `care_relationships` — relationships between entities (elder ↔ caregiver, etc.)
- `emergency_contacts` — contact info for emergencies
- `medical_profiles` — medical history and conditions
- `consent_records` — HIPAA consent tracking
- `care_plans` — care plans for elders
- `health_preferences` — personal health preferences
- `health_vitals` — aggregated health vitals (see `app/models/health_vitals.py`)

**AI Memory (pgvector-based):**
- `ai_conversations` — conversation root aggregate (see `app/models/ai_memory.py`)
  - Fields: tenant_id, user_id, title, conversation_type, status, metadata_json, deleted_at (soft delete)
- `ai_messages` — immutable conversation message ledger
  - Fields: conversation_id, role (system/user/assistant), content, content_hash (SHA256 for dedup), recorded_at (timezone-aware)
- `ai_memory_chunks` — retrieval units extracted from messages or summaries
  - Fields: chunk_text, chunk_hash, chunk_index, chunk_type, message_id (XOR summary_id via CHECK constraint)
- `ai_memory_embeddings` — vector embeddings (1536 dims)
  - Fields: chunk_id, embedding (vector type), embedding_model, content_hash (for re-embed detection on content change), embedded_at
  - Index: IVFFlat cosine on embedding column for semantic search
- `ai_memory_summaries` — compressed conversation windows
  - Fields: conversation_id, summary_text, summary_hash (for dedup), source_window_start_at/end_at, summary_version
- `ai_context_windows` — prompt selection bookkeeping
  - Fields: conversation_id, window_start_at/end_at, token_budget, tokens_used, selection_strategy
- `ai_memory_links` — provenance edges (conversation lineage)
  - Fields: source_type/id, target_type/id, relation_type, weight, deleted_at

Indices and performance

**General patterns:**
- `tenant_id` indexed on all tables (mandatory for multi-tenant filtering)
- `created_at`, `updated_at`, `recorded_at` indexed for time-range queries
- Composite indexes on common filter combinations (e.g., `(tenant_id, user_id)`, `(tenant_id, created_at DESC)`)
- Avoid cross-tenant queries without explicit `WHERE tenant_id = ?`

**Telemetry indexes:**
- `idx_device_telemetry_recorded_at` — for time-range queries on TimescaleDB hypertable
- `idx_vital_stream_events_checksum` — for idempotency (duplicate detection)
- `idx_device_heartbeat_device_timestamp` — for device health monitoring

**AI Memory indexes (35 total):**
- Tenant + composite indexes: `(tenant_id, user_id)`, `(tenant_id, conversation_id)`, `(tenant_id, created_at DESC)`
- Content dedup indexes: `(tenant_id, content_hash)` on messages, chunks, embeddings, summaries
- Vector search index: **IVFFlat cosine** on `ai_memory_embeddings.embedding` for semantic search
  - Built with `lists=100` for 1536-dim vectors
  - Supports `<->` (cosine distance) and `-<>` (negative cosine for ranking)
- Link provenance: `(tenant_id, source_type, source_id)` and `(target_type, target_id)`
- Soft delete awareness: all repository queries filter `WHERE deleted_at IS NULL`

Migrations workflow

1. Edit SQLAlchemy models under `app/models/`.
2. Create alembic revision:

```bash
alembic revision --autogenerate -m "describe change"
```

3. Review and edit the generated migration in `alembic/versions/` — ensure Timescale `create_hypertable` calls align with columns present.
4. Apply migrations:

```bash
alembic upgrade head
```

5. For local development, to drop and recreate DB safely use test/dev scripts (see `docs/LOCAL_DEVELOPMENT.md`).

Backups and disaster recovery

- Use Postgres backups (pg_dump / PITR) combined with Timescale continuous backup patterns for production.

Why this document matters

It captures the current schema & Timescale usage and the exact migration steps developers must follow — important for production migrations and DB ops.

Which modules this documents

- **ORM models:** `app/models/*` (25 models across tenant, user, auth, healthcare, streams, alerts, RBAC, AI memory)
- **Migrations:** `alembic/versions/*` (13 migrations, deterministic naming YYYYMMDD_HHMM_description.py)
- **Database infrastructure:** `app/db/base.py` (Base, UUIDPrimaryKeyMixin, TimestampMixin), `app/db/session.py`, `app/db/async_session.py`
- **Repository access patterns:** `app/repositories/*` (thin data access with tenant isolation and soft delete)
