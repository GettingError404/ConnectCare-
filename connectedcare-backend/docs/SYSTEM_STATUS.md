# System Status — ConnectedCare+

Last verified against repository state: 2026-05-09

## Implementation Matrix

| Subsystem | Status | Implementation Notes | Major Limitations | Future Work |
|---|---|---|---|---|
| Authentication | IMPLEMENTED | JWT access tokens, refresh token rotation, session tracking in `app/models/auth.py`, auth endpoints in `app/api/v1/auth.py` | Uses synchronous DB session patterns | Add stronger token revocation/rotation hardening if needed |
| RBAC | IMPLEMENTED | `Permission`, `Role`, `RolePermission`, `UserRole` models and dependencies in `app/dependencies/authorization.py` | Route coverage is incomplete outside documented routers | Expand route-level permission coverage consistently |
| Tenant isolation | IMPLEMENTED | Tenant context middleware and tenant-scoped repositories | Some routers still rely on `request.state.tenant_id` conventions | Normalize tenant extraction and validation paths |
| Healthcare ingestion | IMPLEMENTED | `healthcare.py` router, healthcare services, repositories, and models | No async intake pipeline beyond current request handling | Add operational monitoring and bulk import support if required |
| Streaming | IMPLEMENTED | MQTT ingestion, telemetry persistence, alert integration, WebSocket broadcast | Routing and handler paths are split across services and routers | Consolidate docs and standardize route prefixes |
| Alert engine | IMPLEMENTED | `app.services.alert_engine`, alert models, alert repositories, alert routes | Alert rule APIs are spread across multiple router patterns | Unify alert API surface where practical |
| AI memory persistence | IMPLEMENTED | `app/models/ai_memory.py`, `app/repositories/ai_memory.py`, migration `20260508_2100_add_ai_memory_persistence.py` | No orchestration/prompting layer exists | Keep persistence-only scope unless planning changes |
| Vector search | IMPLEMENTED | pgvector vector column and semantic search in `app/repositories/ai_memory.py` | Search is repository-level, not exposed as a public API | Add explicit service/API only if required later |
| Celery workers | IMPLEMENTED | Queue topology and task classes in `app/workers`, Celery app in `app/core/celery_app.py` | Workers currently cover AI memory only | Add more tasks only if there is real demand |
| AI orchestration | NOT IMPLEMENTED | No orchestration modules exist under `app/ai/` | None because feature is absent | Do not document as implemented until code exists |
| Prompt assembly | NOT IMPLEMENTED | No prompt builder modules exist | None because feature is absent | Future only |
| Retrieval pipeline | NOT IMPLEMENTED | No retrieval pipeline modules exist beyond AI memory semantic search | None because feature is absent | Future only |
| Context engineering | NOT IMPLEMENTED | No context assembly modules exist | None because feature is absent | Future only |
| Observability | IMPLEMENTED | Structured logging, Prometheus metrics, request and Celery instrumentation | No OpenTelemetry span pipeline is present | Add tracing only if code is introduced |
| Metrics | IMPLEMENTED | `app/core/metrics.py` counters/gauges/histograms, `/metrics` endpoint in `app.main` | Cardinality must be kept low | Keep labels stable and documented |
| CI/CD | IMPLEMENTED | `.github/workflows/*.yml` present for test, quality, security, performance, integration | Workflow behavior not validated in this pass | Keep workflow docs synchronized with code changes |
| WebSockets | IMPLEMENTED | `app/api/v1/ws_alerts.py` websocket endpoint and broadcast manager | One websocket module with Redis pub/sub listener | Expand only if a real use case appears |
| Device ingestion | IMPLEMENTED | MQTT service and telemetry ingestion pipeline | Strongly tied to current telemetry schema | Document route/handler changes when they happen |
| TimescaleDB | IMPLEMENTED | `device_telemetry` hypertable in migrations | Only telemetry uses Timescale-specific behavior | Keep hypertable docs aligned with migrations |
| pgvector | IMPLEMENTED | `ai_memory_embeddings.embedding` vector column and cosine search index | Single embedding dimension and search path today | Avoid documenting unsupported vector features |
| Redis | IMPLEMENTED | Used for Celery broker/backend, pub/sub alerts, cooldown state, websocket listener | Mixed operational roles require careful config | Separate operational guidance from code facts |
| MQTT | IMPLEMENTED | `app.services.mqtt_service` and startup wiring in `app.main` | Broker/service availability affects startup behavior | Expand only with real broker logic changes |

## Notes

- This repository has implemented AI memory persistence and async worker infrastructure, but **not** AI orchestration or prompt assembly.
- Documentation under `docs/` should be treated as implementation-facing only when the corresponding code exists.
- Placeholder documents for future features are explicitly marked as planned, not implemented.
