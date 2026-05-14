# Debugging Guide — ConnectedCare+

STATUS: IMPLEMENTED
Last verified against repository state: 2026-05-09

Purpose

Practical debugging steps linked to the existing codebase, focusing on common failure points: OpenAPI errors, migrations, ingestion pipeline, alert engine, and WebSocket delivery.

OpenAPI generation failures

- Symptom: `PydanticInvalidForJsonSchema: Cannot generate a JsonSchema for core_schema.CallableSchema`.
- Cause: route signature where a `Request` or other concrete type was declared as `Depends()` (e.g. `request: Request = Depends()`).
- Fix: change to accept the `Request` directly (`request: Request`) and ensure parameter order does not violate Python's default ordering.
- Files to inspect: `debug_openapi.py` (project root), `app/api/v1/*`.

Database migration failures

- Symptom: alembic upgrade errors about missing columns or hypertable creation failures.
- Cause: Alembic `create_hypertable` call does not match the model column names or primary key assumptions.
- Fix: edit generated revision in `alembic/versions/*` to align hypertable creation with model columns (e.g., ensure `recorded_at` exists).

Ingest pipeline failures

- Symptoms: missing telemetry persisted, `ingestion_failure_logs` filled.
- Inspect:
  - `app.services.mqtt_service` — confirm messages received by MQTT manager
  - `app.services.ingest_service.persist_event` — check dedupe logic and DB writes
  - `app.services.event_bus` — check Redis publish success
- Useful commands:

```bash
# tail logs
venv\Scripts\python.exe -m uvicorn app.main:app --reload
# in another shell
curl -sS http://127.0.0.1:8000/metrics | grep cc_ingest
```

Alert Engine debug

- Check `app.services.alert_engine` for rule evaluation errors; logs include `Failed evaluating rule` exceptions.
- Check Redis for cooldown keys (`alert:cooldown:{tenant_id}:{rule_id}`).

WebSocket delivery issues

- Confirm Redis pubsub listener is running: `start_alert_bus_listener` in `app/api/v1/ws_alerts.py` starts a background thread that subscribes to `alerts`.
- If broadcasts not delivered, check `ws_alerts.WebSocketManager.active` for connected clients and review `ws_alerts` logs for send exceptions.

Metrics troubleshooting

- If metrics missing with multiple workers, check `PROMETHEUS_MULTIPROC_DIR` and ensure it is writable by worker processes.
- Validate single-process metrics by running `uvicorn` without `--workers` and curling `/metrics`.

Common commands

```bash
# run a single test
venv\Scripts\python.exe -m pytest tests/test_metrics.py -q
# generate openapi programmatically to locate failing routes
venv\Scripts\python.exe - <<PY
from app.main import app
from fastapi.openapi.utils import get_openapi
spec = get_openapi(title='check', version='0', routes=app.routes)
print('paths=', len(spec.get('paths', {})))
PY
```

Why this document matters

Developers will save time by following deterministic debugging steps tied to code paths that previously caused issues.

Which modules this documents

- `app/api/v1/*`, `app/services/ingest_service.py`, `app/services/alert_engine.py`, `app/api/v1/ws_alerts.py`, `alembic/`.

## Limitations

- Several route prefixes are inconsistent across router files and `app.main` registrations.

## Future Work

- Extend this guide only when new failure modes are observed in the repository.
