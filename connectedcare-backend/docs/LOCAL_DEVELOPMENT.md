# Local Development — ConnectedCare+

STATUS: IMPLEMENTED
Last verified against repository state: 2026-05-09

Purpose

Concrete steps to run the application locally with minimal services for development and testing.

Prerequisites

- Python 3.14
- PostgreSQL 15 with TimescaleDB extension
- Redis 7
- MQTT broker only if you plan to exercise device ingestion manually; it is not provided in `docker-compose.yml`

Quick Docker Compose (example)

The repository's `docker-compose.yml` currently includes `postgres-db`, `redis`, `backend`, `worker`, and `flower`. Use the example below only if you need a stripped-down local stack:

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: connectedcare
    volumes:
      - ./pgdata:/var/lib/postgresql/data
    ports:
      - '5432:5432'

  redis:
    image: redis:7
    ports:
      - '6379:6379'

  mqtt:
    image: eclipse-mosquitto:2
    ports:
      - '1883:1883'
```

Environment variables (sample)

Set these in a `.env` or your shell for local dev:

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/connectedcare
REDIS_URL=redis://localhost:6379/0
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
USE_CELERY=false
```

Run locally

```bash
venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Run migrations

```bash
alembic revision --autogenerate -m "message"
alembic upgrade head
```

Run with multiprocessing for load testing (prometheus multiprocess)

```bash
set PROMETHEUS_MULTIPROC_DIR=c:\tmp\prometheus
mkdir c:\tmp\prometheus
venv\Scripts\python.exe -m uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
```

Why this document matters

Developers need a reliable recipe to bootstrap the stack and mimic production behaviors such as Prometheus multiprocess, Timescale hypertable creation, and Redis availability.

Which modules this documents

- `alembic/`, `app/main.py`, `app/services/mqtt_service.py`, `app/core/metrics.py`, `docker-compose.yml`.

## Limitations

- The compose file does not currently define an MQTT broker service.

## Future Work

- Add MQTT to compose only when a real broker service is needed for development.
