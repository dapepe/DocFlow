"""
Request ID middleware for distributed tracing.

Generates or extracts request IDs from headers and stores them in contextvars
for use throughout the request lifecycle. Enables request tracing across logs.
"""

import uuid
from contextvars import ContextVar
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable to store request ID across async boundaries
request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that manages request IDs for distributed tracing.

    - Extracts X-Request-ID header if present
    - Generates UUID if header is missing
    - Stores in contextvars for access in logs
    - Adds X-Request-ID to response headers
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and manage request ID context.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware/handler in the chain

        Returns:
            The HTTP response with X-Request-ID header added
        """
        # Extract request ID from header or generate new one
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Set context variable for this request
        token = request_id_ctx_var.set(request_id)

        try:
            # Process the request
            response = await call_next(request)
        finally:
            # Reset context variable
            request_id_ctx_var.reset(token)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response
