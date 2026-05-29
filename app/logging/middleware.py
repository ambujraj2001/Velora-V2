import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logging.context import bind_context, clear_context
from app.logging.setup import get_logger

log = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        bind_context(request_id=request_id)

        path = request.url.path
        method = request.method
        client_host = request.client.host if request.client else None

        start = time.perf_counter()
        log.info(
            "http.request.started",
            method=method,
            path=path,
            client_host=client_host,
        )

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log.info(
                "http.request.completed",
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log.exception(
                "http.request.failed",
                method=method,
                path=path,
                duration_ms=duration_ms,
            )
            raise
        finally:
            clear_context()
