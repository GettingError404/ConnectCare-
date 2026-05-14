# ConnectedCare+ Backend

STATUS: IMPLEMENTED
Last verified against repository state: 2026-05-09

Enterprise multi-tenant healthcare telemetry platform with AI-powered memory, real-time alerting, and distributed processing.

## Overview

**Technologies:**
- **API:** FastAPI with async/await for high-performance HTTP endpoints
- **Database:** PostgreSQL 14+ with TimescaleDB (time-series) and pgvector (AI embeddings)
- **ORM:** SQLAlchemy 2.0 with async sessions and relationship management
- **Async Tasks:** Celery 5.x with Redis broker (embedding generation, conversation summarization)
- **Real-time:** WebSocket notifications, Redis pub/sub event bus, MQTT device ingestion
- **Observability:** Structured JSON logging with contextvars, Prometheus metrics
- **Authentication:** JWT tokens with refresh token rotation and family-based reuse detection
- **Multi-tenancy:** Tenant isolation at middleware, service, and repository layers

**Features Implemented:**
- **Multi-tenant SaaS:** Tenant/Organization/OrganizationUnit hierarchy with RBAC
- **Device Telemetry:** MQTT ingestion → TimescaleDB hypertable with deduplication
- **Alert Engine:** Threshold-based rules with cooldown, escalation, and WebSocket broadcast
- **Healthcare Domain:** Elders, caregivers, doctors, family members, medical profiles, care plans
- **AI Memory System:** Conversation persistence, semantic search with pgvector, window-based summarization
- **Async Workers:** Priority-based queue topology (5 queues), exponential backoff retry, dead-letter handling
- **Observability:** 10+ metric types, structured request/error logging, distributed tracing prep

## Quick Start

### Prerequisites
- Python 3.14+
- PostgreSQL 14+ with pgvector extension
- Redis 6.0+
- MQTT broker (optional, for device ingestion)
- Docker & docker-compose (optional)

### Local Development (1 command)

```bash
# 1. Install dependencies
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# 2. Start PostgreSQL, Redis, MQTT (via Docker Compose)
docker-compose up -d

# 3. Run migrations (creates 13 migration revisions, including AI memory tables)
alembic upgrade head

# 4. Start API server
uvicorn app.main:app --reload

# 5. Start Celery workers (in another terminal)
celery -A app.core.celery_app worker -l info -Q embedding,summarization,memory,retry

# 6. Access:
# - API docs: http://localhost:8000/docs
# - Metrics: http://localhost:8000/metrics
# - Swagger: http://localhost:8000/openapi.json
```

## Project Structure

```
app/
  main.py                    # FastAPI app, lifespan hooks, middleware registration
  api/v1/                    # REST & WebSocket routers
    auth.py                  # Login, register, token refresh (JWT + family tracking)
    tenants.py               # Tenant and organization management
    rbac.py                  # Role and permission endpoints
    healthcare.py            # Elder, caregiver, care plan management
    telemetry.py             # Device telemetry endpoints (if HTTP ingestion)
    alerts.py                # Alert rule and event management
    devices.py               # Device registration and configuration
    vitals.py                # Vital signs endpoints
    ws_alerts.py             # WebSocket subscription for real-time alerts
  core/
    main.py                  # App configuration entry point
    config.py                # Settings via pydantic-settings
    logging.py               # JSON structured logging with contextvars
    metrics.py               # Prometheus counters, histograms, gauges (including AI metrics)
    celery_app.py            # Celery factory, signal instrumentation, task lifecycle
    security.py              # JWT token creation/validation, password hashing
  models/                    # 25 SQLAlchemy ORM models
    tenant.py                # Tenant, Organization, OrganizationUnit
    user.py                  # User model with tenant_id FK
    auth.py                  # UserSession (JWT sessions), RefreshToken (opaque + family_id)
    rbac.py                  # Permission, Role, RolePermission, UserRole
    healthcare.py            # Elder, Caregiver, Doctor, FamilyMember, CareRelationship, MedicalProfile, CarePlan, etc.
    device.py                # Device model
    streams.py               # VitalStreamEvent (ingest), DeviceTelemetry (TimescaleDB), VitalThreshold, VitalAnomaly, etc.
    alerts.py                # AlertRule, AlertEvent, AlertEscalation
    ai_memory.py             # AIConversation, AIMessage, AIMemoryChunk, AIMemoryEmbedding, AIMemorySummary, AIContextWindow, AIMemoryLink
    health_vitals.py         # HealthVital model
  repositories/              # Data access layer (thin, no business logic)
    auth.py                  # UserSession, RefreshToken persistence
    alerts.py                # AlertRule, AlertEvent queries
    healthcare.py            # Healthcare entity queries
    rbac.py                  # Permission, Role, UserRole queries
    streams.py               # VitalStreamEvent, DeviceTelemetry queries
    tenant.py                # Tenant, Organization queries
    ai_memory.py             # Conversation, message, chunk, embedding, summary CRUD + semantic search via pgvector
  services/                  # Business logic layers
    auth_service.py          # Token generation, refresh rotation, user creation
    mqtt_service.py          # MQTT client lifecycle and message dispatch
    ingest_service.py        # Event deduplication, persistence, EventBus publishing
    alert_engine.py          # Rule evaluation, event generation, escalation
    notification_service.py  # Notification message generation for multiple channels
    healthcare.py            # Healthcare entity management
    rbac.py                  # Permission and role assignment
    tenant.py                # Tenant provisioning
    ai_memory_task_service.py # High-level API for enqueueing AI memory tasks with priority
    event_bus.py             # Redis pub/sub for cross-process event routing
    base.py                  # Shared service utilities
  workers/                   # Celery task workers
    __init__.py              # Queue topology (5 queues), retry config, base task classes
    embedding_worker.py      # EmbeddingTask: generate 1536-dim vectors, pgvector storage, idempotent
    summarization_worker.py  # SummarizationTask: compress conversation windows, hash-based dedup
  middleware/                # HTTP middleware stack (order matters)
    tenant_context.py        # Extract tenant_id from JWT, attach to request.state
    logging_middleware.py    # Request/response lifecycle logging with contextvars
    metrics_middleware.py    # HTTP request/response metrics (duration, status)
    request_id.py            # Generate and propagate X-Request-ID correlation IDs
  db/                        # Database infrastructure
    base.py                  # DeclarativeBase, UUIDPrimaryKeyMixin, TimestampMixin
    session.py               # Async SQLAlchemy session factory
    async_session.py         # Session management utilities
  dependencies/              # FastAPI dependency injection
    authorization.py         # Tenant and RBAC permission checks
  tasks/                     # Directory for future scheduled/periodic tasks

alembic/
  env.py                     # Alembic configuration and execution environment
  versions/                  # 13 deterministic migration files (YYYYMMDD_HHMM pattern)
    20260506_1609_initial_schema.py
    20260506_1705_add_password_hash_and_device_name.py
    20260506_1900_create_alerts.py
    20260508_1100_add_tenants.py
    20260508_1130_add_users_tenant_id.py
    20260508_1200_add_rbac_tables.py
    20260508_1210_seed_rbac_permissions_roles.py  # Populates default permissions/roles
    20260508_1300_add_healthcare.py
    20260508_1310_update_devices.py
    20260508_1320_add_streams.py              # TimescaleDB hypertable setup
    20260508_1330_add_alerts.py
    20260508_2000_add_auth_sessions.py        # UserSession + RefreshToken
    20260508_2100_add_ai_memory_persistence.py # pgvector, 7 AI memory tables, 35 indexes

tests/
  conftest.py                # Shared pytest fixtures, test DB setup
  factories.py               # SQLAlchemy model factories for test data generation
  test_ai_memory_*.py        # 3 files: ORM models, migrations, workers tests
  test_auth_services.py
  test_alert_engine.py
  test_api_openapi.py
  test_e2e.py
  test_healthcare.py
  test_ingestion.py
  test_metrics.py
  test_migrations.py
  test_pipeline_integration.py
  test_rbac.py

docs/                        # Comprehensive documentation (22 files)
  ARCHITECTURE.md            # High-level component interactions and data flows
  BACKEND_STRUCTURE.md       # Folder map and module responsibilities
  DATABASE.md                # 25 tables, pgvector, indexes, migration workflow
  AUTH_SYSTEM.md             # JWT, refresh tokens, RBAC, tenant isolation
  ASYNC_WORKERS.md           # Celery queue topology, retry strategy, task implementations
  OBSERVABILITY.md           # Logging, metrics, Prometheus, dashboards
  AI_MEMORY_PERSISTENCE_IMPLEMENTATION.md # ORM, migration, repository, tests (1600+ lines)
  ASYNC_AI_MEMORY_PROCESSING.md # Workers, task service, queue topology (1460+ lines)
  STREAM_PIPELINE.md         # MQTT → Ingest → AlertEngine → WebSocket flow
  ALERT_ENGINE.md            # Rule evaluation, cooldown, escalation
  MIGRATION_GUIDE.md         # How to create and apply migrations safely
  LOCAL_DEVELOPMENT.md       # Docker setup, environment variables, local commands
  API_OVERVIEW.md            # REST endpoints and authentication
  [7 more docs]

docker-compose.yml           # PostgreSQL, Redis, MQTT (local dev)
Dockerfile                   # Container image for production deployment
pytest.ini                   # pytest configuration
requirements.txt             # Python dependencies (FastAPI, SQLAlchemy, Celery, etc.)
alembic.ini                  # Alembic configuration
.env.example                 # Example environment variables
.github/workflows/           # CI/CD pipelines (test, quality, security, performance, integration)
```

## Database Schema Highlights

**25 SQLAlchemy ORM Models** across these categories:

| Category | Models | Purpose |
|----------|--------|---------|
| **Multi-tenancy** | Tenant, Organization, OrganizationUnit | Tenant hierarchy |
| **Users & Auth** | User, UserSession, RefreshToken | User management + JWT session tracking |
| **RBAC** | Permission, Role, RolePermission, UserRole | Fine-grained role-based access control |
| **Healthcare** | Elder, Caregiver, Doctor, FamilyMember, CareRelationship, EmergencyContact, MedicalProfile, ConsentRecord, CarePlan, HealthPreferences | Domain models for elder care |
| **Devices & Streams** | Device, VitalStreamEvent, DeviceTelemetry (TimescaleDB), VitalThreshold, VitalAnomaly, DeviceHeartbeat, IngestionFailureLog, HealthVital | Device telemetry with time-series storage |
| **Alerts** | AlertRule, AlertEvent, AlertEscalation, Alert | Alert rule definitions and event history |
| **AI Memory** | AIConversation, AIMessage, AIMemoryChunk, AIMemoryEmbedding, AIMemorySummary, AIContextWindow, AIMemoryLink | Conversation persistence with semantic search |

**Key Features:**
- All tables include `tenant_id` (mandatory foreign key) for multi-tenant isolation
- Soft delete via `deleted_at` timestamp (data retention without hard deletion)
- UUID primary keys (server-generated)
- Timezone-aware timestamps (`created_at`, `updated_at`)
- **35+ indexes** for performance (tenant+composite, dedup hashes, pgvector IVFFlat)
- **pgvector column** in `ai_memory_embeddings` for 1536-dim OpenAI embeddings with cosine distance search

## API Endpoints (Quick Reference)

| Router | Base Path | Purpose |
|--------|-----------|---------|
| auth | `/api/v1/auth` | Login, register, refresh tokens, logout |
| tenants | `/api/v1/tenants` | Tenant management and provisioning |
| rbac | `/api/v1/rbac` | Permission and role management |
| healthcare | `/api/v1/healthcare` | Elder, caregiver, care plan management |
| telemetry | `/api/v1/telemetry` | Device telemetry endpoints (if HTTP ingestion) |
| alerts | `/api/v1/alerts` | Alert rules and event listing |
| devices | `/api/v1/devices` | Device registration and configuration |
| vitals | `/api/v1/vitals` | Vital signs and health data |
| ws_alerts | `/api/v1/ws/alerts` | **WebSocket** for real-time alert subscriptions |

**Authentication:** JWT Bearer token (refresh token rotation with family-based reuse detection)

## Async Task Queues (Celery)

**5 Queues with priorities:**
1. **embedding** (priority=10) — Generate 1536-dim vectors for conversation chunks (4-8 workers)
2. **summarization** (priority=8) — Compress conversation windows (2-4 workers)
3. **memory** (priority=5) — Batch enqueue children tasks (1-2 workers)
4. **retry** (priority=1) — Exponential backoff queue for failed tasks (1-2 workers)
5. **dead_letter** (priority=0) — Permanent failures for manual inspection (no workers)

**Retry Strategy:** Exponential backoff (1s → 2s → 4s → 8s → 16s, max 5 retries), then dead-letter

**Metrics:** 6 AI memory counters (embeddings_generated, embeddings_failed, summaries_generated, summaries_failed, chunks_created, searches)

## Observability

**Logging:**
- Structured JSON logs with context fields (request_id, tenant_id, user_id, trace_id)
- Contextvars propagated through middleware → services → workers

**Metrics (Prometheus):**
- HTTP: `cc_http_requests_total`, `cc_http_request_duration_seconds`
- Telemetry: `cc_mqtt_messages_total`, `cc_ingest_events_total`, `cc_alerts_triggered_total`
- AI Memory: `cc_ai_memory_embeddings_generated_total`, `cc_ai_memory_summaries_generated_total`, etc.
- Celery: Per-task success/failure/retry counters and latency histograms
- Endpoint: `/metrics` (Prometheus format)

**Tracing:**
- Trace ID generation and context propagation ready for OpenTelemetry integration

## Running Tests

```bash
# All tests (unit + integration)
pytest -v

# Specific test file
pytest tests/test_ai_memory_models.py -v

# With coverage
pytest --cov=app tests/ --cov-report=html

# Watch mode (requires pytest-watch)
ptw
```

**Test Coverage:**
- ORM models, relationships, constraints, soft delete, indexes
- Migrations (schema validation, rollback, idempotence)
- Worker tasks (queue routing, retry, error handling, tenant isolation)
- API endpoints (auth, RBAC, healthcare)
- Alert engine (rule evaluation, cooldown)
- Full integration tests (MQTT → ingest → alerts → WebSocket)

## Deployment

**Docker:**
```bash
docker build -t connectedcare-backend:latest .
docker run -d \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  -p 8000:8000 \
  connectedcare-backend:latest
```

**Environment Variables:**
```bash
DATABASE_URL=postgresql://user:pass@localhost/connectedcare
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
ENABLE_MQTT=false  # Set true to enable MQTT ingestion
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus  # For multiprocess metrics
```

## Documentation

Comprehensive documentation in `docs/`:

- **Architecture & Design:** [ARCHITECTURE.md](docs/ARCHITECTURE.md), [BACKEND_STRUCTURE.md](docs/BACKEND_STRUCTURE.md)
- **Database:** [DATABASE.md](docs/DATABASE.md), [MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md)
- **Auth & Security:** [AUTH_SYSTEM.md](docs/AUTH_SYSTEM.md)
- **Async Processing:** [ASYNC_WORKERS.md](docs/ASYNC_WORKERS.md)
- **AI Memory:** [AI_MEMORY_PERSISTENCE_IMPLEMENTATION.md](docs/AI_MEMORY_PERSISTENCE_IMPLEMENTATION.md), [ASYNC_AI_MEMORY_PROCESSING.md](docs/ASYNC_AI_MEMORY_PROCESSING.md)
- **Operations:** [OBSERVABILITY.md](docs/OBSERVABILITY.md), [LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md), [STREAM_PIPELINE.md](docs/STREAM_PIPELINE.md)

## Key Entry Points for Code Reading

1. **HTTP API:** Start with [app/main.py](app/main.py) → [app/api/v1/](app/api/v1) routers
2. **Data Model:** [app/models/ai_memory.py](app/models/ai_memory.py) (AI memory) or [app/models/healthcare.py](app/models/healthcare.py) (domain)
3. **Async Processing:** [app/workers/](app/workers) → [app/services/ai_memory_task_service.py](app/services/ai_memory_task_service.py)
4. **Telemetry Pipeline:** [app/services/mqtt_service.py](app/services/mqtt_service.py) → [app/services/ingest_service.py](app/services/ingest_service.py) → [app/services/alert_engine.py](app/services/alert_engine.py)
5. **Database Access:** [app/db/base.py](app/db/base.py) (mixins) → [app/repositories/](app/repositories) (thin access layer)
6. **Observability:** [app/core/logging.py](app/core/logging.py) (JSON logs) + [app/core/metrics.py](app/core/metrics.py) (Prometheus)

## FAQ & Troubleshooting

**Q: How do I add a new database table?**
- Edit model in `app/models/` (include `tenant_id` FK + mixins)
- Run `alembic revision --autogenerate -m "describe"`
- Review and run migration: `alembic upgrade head`
- Add repository in `app/repositories/`
- See [MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md)

**Q: How do I enqueue a background task?**
- Use `AIMemoryTaskService.enqueue_*()` methods with priority (PRIORITY_CRITICAL, PRIORITY_HIGH, etc.)
- Or create new task in `app/workers/`, call `.apply_async(queue=...)`
- See [ASYNC_WORKERS.md](docs/ASYNC_WORKERS.md)

**Q: How do I add a new API endpoint?**
- Create router in `app/api/v1/` with FastAPI `@router.get/post/etc.`
- Use `Depends(require_permission("action"))` for RBAC
- Register router in `app/main.py` via `app.include_router()`
- See [AUTH_SYSTEM.md](docs/AUTH_SYSTEM.md) and [API_OVERVIEW.md](docs/API_OVERVIEW.md)

**Q: Where are Prometheus metrics exposed?**
- Endpoint: `http://localhost:8000/metrics`
- Metrics code: [app/core/metrics.py](app/core/metrics.py)
- Instrumentation: HTTP middleware, Celery signals, explicit counter increments

**Q: How do I debug a failed worker task?**
- Check Celery logs: `celery -A app.core.celery_app inspect active` (current tasks)
- Check dead-letter queue: tasks exceeding max retries (5) end up here
- Monitor queue depth: `celery -A app.core.celery_app inspect stats | grep messages`
- See [DEBUGGING_GUIDE.md](docs/DEBUGGING_GUIDE.md) and [OBSERVABILITY.md](docs/OBSERVABILITY.md)

## Contributing

- Follow existing patterns in `app/models`, `app/repositories`, `app/services`
- Add tests for new features (pytest, conftest fixtures)
- Update docs if adding major features
- Run `pytest` before submitting PR

## License & Support

[Add your license and support info here]
