import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

# Context for per-request correlation
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """Inject request_id from contextvars into every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """Minimal JSON formatter for structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        base: Dict[str, Any] = {
            "ts": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }

        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)

        # Include extra fields (anything not part of the standard LogRecord)
        for key, value in record.__dict__.items():
            if key in (
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
            ):
                continue
            if key not in base:
                base[key] = value

        return json.dumps(base, default=str)


def configure_logging(service_name: str = "pantrypilot-backend", level: str = "INFO") -> None:
    """
    Configure root logger for JSON output, with request_id support.
    Call once at startup before other loggers are created.
    """
    root = logging.getLogger()
    root.setLevel(level)

    # Avoid duplicate handlers if reload is used
    if root.handlers:
        for handler in list(root.handlers):
            root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())
    root.addHandler(handler)

    # Set uvicorn loggers to propagate into root
    for uvicorn_logger in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(uvicorn_logger).handlers = []
        logging.getLogger(uvicorn_logger).propagate = True

    logging.getLogger(__name__).info("Logging initialized", extra={"service": service_name})


def bind_request_id(request_id: Optional[str]) -> None:
    """Store request_id in a contextvar for downstream log records."""
    request_id_var.set(request_id)


def reset_request_id() -> None:
    """Clear request_id context."""
    request_id_var.set(None)
