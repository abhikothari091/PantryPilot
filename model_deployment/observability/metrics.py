import re
import time
from typing import Dict, Optional

from fastapi import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import text
from sqlalchemy.engine import Engine

REQUEST_COUNTER = Counter(
    "pantrypilot_requests_total",
    "HTTP requests",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "pantrypilot_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path", "status"],
    buckets=(
        0.05,
        0.1,
        0.2,
        0.5,
        1,
        2,
        5,
        10,
    ),
)


def normalize_path(path: str) -> str:
    """Reduce high-cardinality segments (e.g., numeric IDs) for metrics labels."""
    return re.sub(r"/\\d+", "/:id", path)


def record_request_metrics(method: str, path: str, status: int, duration_seconds: float) -> None:
    path_label = normalize_path(path)
    REQUEST_COUNTER.labels(method=method, path=path_label, status=str(status)).inc()
    REQUEST_LATENCY.labels(method=method, path=path_label, status=str(status)).observe(duration_seconds)


def collect_health(engine: Engine) -> Dict[str, Optional[str]]:
    """
    Lightweight health probe.
    Attempts a simple DB round trip; never raises.
    """
    db_status = "unknown"
    db_latency_ms: Optional[float] = None
    try:
        start = time.perf_counter()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_latency_ms = round((time.perf_counter() - start) * 1000, 2)
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {exc.__class__.__name__}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
        "db_latency_ms": db_latency_ms,
    }


def metrics_response() -> Response:
    """Prometheus scrape endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
