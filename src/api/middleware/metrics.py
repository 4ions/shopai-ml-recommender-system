import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.infrastructure.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_errors_total,
)

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        method = request.method
        endpoint = request.url.path

        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            status_code = response.status_code

            http_requests_total.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(process_time)

            if status_code >= 400:
                error_type = "client_error" if status_code < 500 else "server_error"
                http_errors_total.labels(method=method, endpoint=endpoint, error_type=error_type).inc()

            return response

        except Exception as e:
            process_time = time.time() - start_time
            status_code = 500

            http_requests_total.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(process_time)
            http_errors_total.labels(method=method, endpoint=endpoint, error_type="server_error").inc()

            logger.error("Request error", method=method, endpoint=endpoint, error=str(e))
            raise

