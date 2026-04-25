from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

_correlation_ctx: ContextVar[dict[str, str] | None] = ContextVar(
    "ai_desk_correlation",
    default=None,
)


def _get_correlation_dict() -> dict[str, str]:
    val = _correlation_ctx.get()
    return val if val is not None else {}


def set_correlation(**fields: str) -> None:
    current = _get_correlation_dict().copy()
    current.update({k: v for k, v in fields.items() if v})
    _correlation_ctx.set(current)


def get_correlation() -> dict[str, str]:
    return _get_correlation_dict().copy()


def clear_correlation() -> None:
    _correlation_ctx.set({})


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        correlation = _get_correlation_dict()
        record.workflow_run_id = correlation.get("workflow_run_id", "")
        record.task_id = correlation.get("task_id", "")
        record.attempt_id = correlation.get("attempt_id", "")
        record.trace_id = correlation.get("trace_id", "")
        record.provider_request_id = correlation.get("provider_request_id", "")
        return True


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=UTC,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        correlation_fields = [
            "workflow_run_id",
            "task_id",
            "attempt_id",
            "trace_id",
            "provider_request_id",
        ]
        for fld in correlation_fields:
            value = getattr(record, fld, "")
            if value:
                log_entry[fld] = value

        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        extra_keys = set(record.__dict__.keys()) - {
            "name",
            "msg",
            "args",
            "created",
            "relativeCreated",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "pathname",
            "filename",
            "module",
            "thread",
            "threadName",
            "process",
            "processName",
            "levelname",
            "levelno",
            "message",
            "msecs",
            "taskName",
        } | set(correlation_fields)
        for key in sorted(extra_keys):
            value = record.__dict__[key]
            if value is not None and not key.startswith("_"):
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False, default=str)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"ai_desk.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        handler.addFilter(CorrelationFilter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def configure_root_logging() -> None:
    root = logging.getLogger("ai_desk")
    if root.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    handler.addFilter(CorrelationFilter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)
