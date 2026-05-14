# Backend Structure — ConnectedCare+

STATUS: IMPLEMENTED
Last verified against repository state: 2026-05-09

Purpose

Map of important folders and files so newcomers can find code quickly and understand responsibilities.

Top-level layout

- `app/`
  - `main.py` — FastAPI app instance, lifespan hooks (MQTT startup/shutdown), middleware registration
  - `api/v1/` — REST and WebSocket API routers
    - `auth.py` — authentication, login, refresh tokens
    - `tenants.py` — tenant management
    - `rbac.py` — role-based access control endpoints
    - `healthcare.py` — elder/caregiver/doctor management
    - `telemetry.py` — device telemetry ingestion endpoints
    - `alerts.py` — alert rule and event management
    - `devices.py` — device registration and configuration
    - `vitals.py` — vital signs and health data
    - `ws_alerts.py` — WebSocket connection for real-time alert notifications
  - `core/` — infrastructure and configuration
    - `logging.py` — structured JSON logging with contextvars (request_id, tenant_id, user_id, trace_id)
    - `metrics.py` — Prometheus counters, histograms, gauges (HTTP, Celery, AI memory)
    - `celery_app.py` — Celery app factory, signal instrumentation, task lifecycle hooks
    - `config.py` — environment settings via pydantic-settings
  - `db/` — database infrastructure
    - `base.py` — SQLAlchemy Base class and mixins (UUIDPrimaryKeyMixin, TimestampMixin)
    - `session.py` — async SQLAlchemy session factory and management
    - `async_session.py` — session utilities
  - `models/` — SQLAlchemy ORM models (25 models total, 13 migrations applied)
    - `tenant.py` — Tenant, Organization, OrganizationUnit (multi-tenant hierarchy)
    - `user.py` — User model with tenant_id foreign key
    - `auth.py` — UserSession, RefreshToken (JWT token management)
    - `rbac.py` — Permission, Role, RolePermission, UserRole (role-based access control)
    - `healthcare.py` — Elder, Caregiver, Doctor, FamilyMember, CareRelationship, EmergencyContact, MedicalProfile, ConsentRecord, CarePlan, HealthPreferences
    - `device.py` — Device model
    - `streams.py` — VitalStreamEvent (ingest events), DeviceTelemetry (TimescaleDB hypertable), VitalThreshold, VitalAnomaly, DeviceHeartbeat, IngestionFailureLog
    - `alerts.py` — AlertRule, AlertEvent, AlertEscalation
    - `alert.py` — Alert (deprecated, see alerts.py)
    - `health_vitals.py` — HealthVital model
    - `ai_memory.py` — AIConversation, AIMessage, AIMemoryChunk, AIMemoryEmbedding, AIMemorySummary, AIContextWindow, AIMemoryLink (AI memory persistence)
  - `repositories/` — thin data access layers with tenant isolation and soft delete support
    - `auth.py` — UserSession and RefreshToken queries
    - `alerts.py` — AlertRule, AlertEvent queries
    - `healthcare.py` — Elder, Caregiver, Doctor, CareRelationship queries
    - `rbac.py` — Permission, Role, UserRole queries
    - `streams.py` — VitalStreamEvent, DeviceTelemetry, VitalThreshold queries
    - `tenant.py` — Tenant, Organization queries
    - `ai_memory.py` — AI memory CRUD: conversations, messages, chunks, embeddings, summaries with semantic search
  - `services/` — business logic layers
    - `auth_service.py` — token generation, validation, refresh logic
    - `mqtt_service.py` — MQTT broker connection and subscription lifecycle
    - `ingest_service.py` — device event deduplication, persistence, event publishing
    - `alert_engine.py` — alert rule evaluation, event generation, escalation
    - `notification_service.py` — notification message generation
    - `healthcare.py` — elder and caregiver management
    - `rbac.py` — permission checking and role assignment
    - `tenant.py` — tenant initialization and management
    - `vitals_service.py` — vital signs processing
    - `device_service.py` — device management
    - `event_bus.py` — Redis pub/sub event routing
    - `ai_memory_task_service.py` — high-level API for enqueuing AI memory tasks with priority routing
    - `base.py` — shared service utilities
  - `workers/` — Celery task workers for async processing
    - `embedding_worker.py` — generates and stores 1536-dimensional OpenAI embeddings for AI memory chunks (idempotent, metrics)
    - `summarization_worker.py` — compresses conversation windows into summaries (idempotent, window-based, metrics)
    - `__init__.py` — queue topology definition (5 queues: embedding, summarization, memory, retry, dead_letter), base task classes (BaseAIMemoryTask, TenantAwareTask), retry strategy (exponential backoff, max 5 retries)
  - `middleware/` — HTTP middleware stack
    - `tenant_context.py` — extracts tenant_id from JWT and attaches to request.state
    - `logging_middleware.py` — request/response lifecycle logging with structured context
    - `metrics_middleware.py` — Prometheus HTTP request/response metrics (duration, status)
    - `request_id.py` — generates and propagates correlation IDs (X-Request-ID header)
  - `dependencies/` — FastAPI dependency injection
    - `authorization.py` — tenant and RBAC verification for routes
  - `tasks/` — directory for additional Celery tasks (currently empty, see workers/ instead)
  - `utils/` — helper functions
    - pagination, response formatting, datetime utilities

- `alembic/` — database migration management
  - `versions/` — 13 migration files (deterministic naming: YYYYMMDD_HHMM_description.py)
    - 20260506_1609: initial_schema
    - 20260506_1705: add_password_hash_and_device_name
    - 20260506_1900: create_alerts
    - 20260508_1100: add_tenants
    - 20260508_1130: add_users_tenant_id
    - 20260508_1200: add_rbac_tables
    - 20260508_1210: seed_rbac_permissions_roles (initial permissions and roles)
    - 20260508_1300: add_healthcare
    - 20260508_1310: update_devices
    - 20260508_1320: add_streams (TimescaleDB hypertable setup)
    - 20260508_1330: add_alerts (AlertRule, AlertEvent, AlertEscalation)
    - 20260508_2000: add_auth_sessions (UserSession, RefreshToken)
    - 20260508_2100: add_ai_memory_persistence (pgvector, 7 AI memory tables, 35 indexes)
  - `env.py` — Alembic configuration and execution environment

- `tests/` — pytest test suite (15 test modules)
  - `conftest.py` — pytest fixtures and configuration
  - `factories.py` — SQLAlchemy model factories for test data generation
  - `test_ai_memory_models.py` — ORM model validation, relationships, constraints, tenant isolation, soft delete, indexes
  - `test_ai_memory_migration.py` — migration schema validation, rollback, idempotence
  - `test_ai_memory_workers.py` — worker task execution, service API, queue routing, error handling
  - `test_alert_engine.py` — alert rule evaluation
  - `test_api_openapi.py` — OpenAPI spec validation
  - `test_auth_services.py` — authentication and token refresh
  - `test_e2e.py` — end-to-end integration tests
  - `test_healthcare.py` — elder/caregiver operations
  - `test_ingestion.py` — MQTT event ingestion and deduplication
  - `test_metrics.py` — Prometheus metrics collection
  - `test_migrations.py` — Alembic migration validation
  - `test_pipeline_integration.py` — full system integration tests
  - `test_rbac.py` — role and permission validation

- `.github/workflows/` — CI/CD pipelines (5 workflows)
  - `test.yml` — unit and integration tests
  - `python-quality.yml` — lint, format, type checking
  - `security.yml` — security scanning
  - `performance.yml` — performance benchmarks
  - `integration.yml` — full system integration tests

Key code entry points

- HTTP server: `app.main:app` (Uvicorn/Gunicorn)
- MQTT manager: `app.services.mqtt_service.mqtt_manager`
- Celery: `app.core.celery_app.celery_app`

Why this document matters

New developers can map responsibilities to files quickly and avoid searching the whole tree for implementation details.

Which modules this documents

All directories under `app/`; specifically: `app/api/v1`, `app/services`, `app/models`, `app/repositories`, `app/core`, `app/middleware`, `app/workers`, `app/db`, `app/dependencies`; plus `alembic/versions` and `tests/`.
