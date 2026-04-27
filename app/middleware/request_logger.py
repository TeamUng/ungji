import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        method = request.method
        path = request.url.path
        start = time.perf_counter()

        if settings.LOG_LEVEL == "DEBUG":
            content_type = request.headers.get("content-type", "")
            if content_type.startswith("application/json") or content_type.startswith("text/"):
                body = await request.body()
                if body and len(body) < 10_240:
                    logger.debug(
                        "Request body",
                        extra={"request_id": request_id, "body": body.decode(errors="replace")},
                    )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                f"{method} {path} ERROR",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        status = response.status_code
        logger.info(
            f"{method} {path} {status}",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status": status,
                "duration_ms": round(duration_ms, 2),
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response
