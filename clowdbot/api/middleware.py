"""API middleware - rate limiting, request logging, CORS."""

from __future__ import annotations

import logging
import time
from collections import deque

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

__all__ = ["setup_middleware"]

logger = logging.getLogger(__name__)

# Simple in-memory rate limiter
# Using deque per client allows O(k) expiry removal from the front instead of
# O(N) list-comprehension filtering on every request.
_rate_limits: dict[str, deque[float]] = {}
RATE_LIMIT = 60  # requests per window
RATE_WINDOW = 60  # seconds
# Periodically sweep the dict to evict entries for clients that have gone quiet.
_CLEANUP_INTERVAL = 1000  # requests between full sweeps
_request_counter = 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        global _request_counter
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - RATE_WINDOW

        if client_ip not in _rate_limits:
            _rate_limits[client_ip] = deque()

        # Remove expired timestamps from the front of the deque – O(k) where k
        # is the number of expired entries, rather than rebuilding the whole list.
        client_times = _rate_limits[client_ip]
        while client_times and client_times[0] < window_start:
            client_times.popleft()

        if len(client_times) >= RATE_LIMIT:
            return Response(
                content='{"status":"error","error":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
            )

        client_times.append(now)

        # All operations above run without an `await`, so they are atomic within
        # asyncio's single-threaded event loop – no other coroutine can interleave.
        # Periodically evict deques for client IPs that have gone quiet to bound
        # dict growth.  Keys are collected into a list first so the dict is not
        # mutated while iterating over it.
        _request_counter += 1
        if _request_counter >= _CLEANUP_INTERVAL:
            _request_counter = 0
            stale = [ip for ip, times in _rate_limits.items() if not times]
            for ip in stale:
                del _rate_limits[ip]

        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all API requests with timing."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration = (time.monotonic() - start) * 1000
        logger.info(
            "HTTP %s %s → %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        return response


def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware on the FastAPI app."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
