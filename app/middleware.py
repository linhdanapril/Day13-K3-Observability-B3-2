"""
Correlation ID Middleware - CP1

FastAPI/Starlette middleware that:
1. Generates unique correlation IDs for each request
2. Binds correlation ID to structlog context for request tracing
3. Adds correlation ID and response time to response headers
4. Prevents context variable leakage between requests
"""
from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that injects correlation IDs for distributed request tracing.

    Correlation IDs allow tracking a single request across multiple services,
    logs, and trace spans. This is essential for debugging production issues
    where a user request touches multiple components.
    """

    async def dispatch(self, request: Request, call_next):
        # -----------------------------------------------------------------
        # Step 1: Clear contextvars to prevent data leakage between requests
        # This ensures each request starts with a clean slate and doesn't
        # accidentally inherit context from a previous request
        # -----------------------------------------------------------------
        clear_contextvars()

        # -----------------------------------------------------------------
        # Step 2: Extract or generate correlation ID
        # Priority: Use x-request-id header if provided by client/proxy,
        # otherwise generate a new one in format "req-<8-hex-chars>"
        # Example: req-a1b2c3d4
        # -----------------------------------------------------------------
        header_correlation = request.headers.get("x-request-id")
        if header_correlation:
            correlation_id = header_correlation
        else:
            correlation_id = f"req-{uuid.uuid4().hex[:8]}"

        # -----------------------------------------------------------------
        # Step 3: Bind correlation_id to structlog context variables
        # All subsequent log calls in this request chain will automatically
        # include this correlation_id
        # -----------------------------------------------------------------
        bind_contextvars(correlation_id=correlation_id)

        # Store in request state for access in route handlers
        request.state.correlation_id = correlation_id

        # -----------------------------------------------------------------
        # Step 4: Time the request processing
        # Use perf_counter for high-precision timing
        # -----------------------------------------------------------------
        start = time.perf_counter()
        response = await call_next(request)

        # -----------------------------------------------------------------
        # Step 5: Add tracing headers to response
        # x-request-id: allows clients to reference this specific request
        # x-response-time-ms: processing time for monitoring/alerting
        # -----------------------------------------------------------------
        response.headers["x-request-id"] = correlation_id
        response.headers["x-response-time-ms"] = str(int((time.perf_counter() - start) * 1000))

        return response
