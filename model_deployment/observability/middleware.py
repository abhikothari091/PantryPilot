import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .logging_config import bind_request_id, reset_request_id
from .metrics import record_request_metrics
import logging

logger = logging.getLogger("observability")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Adds request_id propagation, structured request logs, and Prometheus metrics.
    """

    def __init__(self, app, service_name: str = "pantrypilot-backend"):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        bind_request_id(request_id)
        request.state.request_id = request_id

        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            duration_sec = time.perf_counter() - start
            path = request.url.path
            status_code = getattr(locals().get("response", None), "status_code", 500)

            logger.info(
                "request_completed",
                extra={
                    "service": self.service_name,
                    "method": request.method,
                    "path": path,
                    "status": status_code,
                    "duration_ms": round(duration_sec * 1000, 2),
                    "user_agent": request.headers.get("user-agent"),
                },
            )
            record_request_metrics(request.method, path, status_code, duration_sec)
            reset_request_id()

        response.headers["x-request-id"] = request_id
        return response
