# DevOps Readiness — ConnectedCare+

Status: implemented with enterprise hardening primitives and deployment scaffolding.

## CI/CD

- Use [.github/workflows/enterprise-ci.yml](../.github/workflows/enterprise-ci.yml) for pull-request and main-branch validation.
- Use [.github/workflows/deploy.yml](../.github/workflows/deploy.yml) for manual Helm deployments.
- Keep the existing quality and integration workflows as specialized checks for code quality and database-backed validation.

## Observability

- Structured logging is emitted from [app/core/logging.py](../app/core/logging.py).
- Request-level trace propagation is handled by [app/middleware/logging_middleware.py](../app/middleware/logging_middleware.py).
- Prometheus metrics remain available at `/metrics`.
- Optional Sentry and OpenTelemetry hooks are initialized from [app/core/observability.py](../app/core/observability.py).

## Kubernetes

- Helm chart: [deploy/helm/connectedcare](../deploy/helm/connectedcare)
- Health probes: `/health` for liveness, `/ready` for readiness
- Default HPA: CPU-based scaling with safe defaults
- Ingress: disabled by default, enable per environment

## Production Guidance

- Put TLS termination at the ingress or reverse proxy layer.
- Feed production secrets through Kubernetes Secrets or an external secrets manager, not ConfigMaps.
- Set `TRUSTED_HOSTS` and `CORS_ALLOW_ORIGINS` per environment.
- Configure `SENTRY_DSN` and `OTEL_EXPORTER_OTLP_ENDPOINT` only where the backend services exist.
- Back up the PostgreSQL volume and test restore procedures before release.
