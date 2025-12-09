## Observability Add-ons (Logging + Metrics)

This folder adds structured logging, request correlation, and Prometheus-friendly metrics for the FastAPI backend.

### What’s included
- `logging_config.py`: JSON formatter, request_id filter, and `configure_logging()`.
- `middleware.py`: injects `x-request-id`, writes structured request logs, and records Prometheus counters/histograms.
- `metrics.py`: request metrics, `/metrics` exporter, and a simple DB-backed `/healthz` probe.

### How it’s wired
`model_deployment/backend/main.py` bootstraps logging and attaches `ObservabilityMiddleware`. Two endpoints are registered:
- `GET /healthz` – lightweight health probe with DB round trip.
- `GET /metrics` – Prometheus scrape endpoint.

### Local scrape example
```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/metrics | head
```
