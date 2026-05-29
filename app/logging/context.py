from contextvars import ContextVar

import structlog

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
tenant_id_var: ContextVar[str | None] = ContextVar("tenant_id", default=None)

LOG_KEY = "X-Request-Id"


def bind_context(**kwargs: str) -> None:
    mapped = {}
    for k, v in kwargs.items():
        if k == "request_id":
            mapped[LOG_KEY] = v
            request_id_var.set(v)
        elif k == "tenant_id":
            mapped[k] = v
            tenant_id_var.set(v)
        else:
            mapped[k] = v
    structlog.contextvars.bind_contextvars(**mapped)


def clear_context() -> None:
    structlog.contextvars.clear_contextvars()
    request_id_var.set(None)
    tenant_id_var.set(None)
