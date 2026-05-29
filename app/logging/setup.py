import logging
import queue
import sys
from logging.handlers import QueueHandler, QueueListener

import structlog

from app.config import settings

_axiom_listener: QueueListener | None = None


class FlushStreamHandler(logging.StreamHandler):
    """Write logs to terminal immediately (no stdout buffering delay)."""

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


def _add_service_context(
    _logger: logging.Logger,
    _method_name: str,
    event_dict: dict,
) -> dict:
    event_dict.setdefault("service", "velora")
    event_dict.setdefault("environment", settings.app_env)
    return event_dict


def _drop_internal_fields(
    _logger: logging.Logger,
    _method_name: str,
    event_dict: dict,
) -> dict:
    event_dict.pop("_record", None)
    event_dict.pop("_from_structlog", None)
    return event_dict


def _ensure_unbuffered_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(line_buffering=True)
        except Exception:
            pass


def setup_logging() -> None:
    global _axiom_listener

    if _axiom_listener is not None:
        _axiom_listener.stop()
        _axiom_listener = None

    _ensure_unbuffered_stdout()

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    timestamper = structlog.processors.TimeStamper(fmt="iso", key="_time")

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        _add_service_context,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    json_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            _drop_internal_fields,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
    )

    console_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            _drop_internal_fields,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(pad_event=40),
        ],
    )

    console_handler = FlushStreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(log_level)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(console_handler)
    root.setLevel(log_level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        named = logging.getLogger(logger_name)
        named.handlers.clear()
        named.propagate = True
        named.setLevel(log_level)

    axiom_enabled = bool(settings.axiom_token)
    if axiom_enabled:
        from axiom_py import Client
        from axiom_py.logging import AxiomHandler

        client = Client(
            token=settings.axiom_token,
            org_id=settings.axiom_org_id or None,
        )
        axiom_handler = AxiomHandler(client, settings.axiom_dataset)
        axiom_handler.setFormatter(json_formatter)
        axiom_handler.setLevel(log_level)

        log_queue: queue.Queue[logging.LogRecord] = queue.Queue(-1)
        queue_handler = QueueHandler(log_queue)
        _axiom_listener = QueueListener(
            log_queue,
            axiom_handler,
            respect_handler_level=True,
        )
        _axiom_listener.start()
        root.addHandler(queue_handler)

    get_logger(__name__).info(
        "logging.configured",
        console=True,
        axiom=axiom_enabled,
        dataset=settings.axiom_dataset if axiom_enabled else None,
        log_level=settings.log_level,
    )


def shutdown_logging() -> None:
    global _axiom_listener
    if _axiom_listener is not None:
        _axiom_listener.stop()
        _axiom_listener = None


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
