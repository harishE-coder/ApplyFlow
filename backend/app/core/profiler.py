"""
ApplyFlow Backend Performance & Query Profiler Middleware.
Provides real-time telemetry on every incoming API request:
- Route and HTTP method
- Number of SQL queries executed
- SQL execution time (in milliseconds)
- Total server-side duration (in milliseconds)
- Visual slow-query alerts for requests exceeding 200ms
"""

import contextvars
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variables to track query count and SQL execution time per async request
_query_count_var = contextvars.ContextVar("query_count", default=0)
_sql_time_var = contextvars.ContextVar("sql_time", default=0.0)
_sql_start_var = contextvars.ContextVar("sql_start", default=0.0)


def record_sql_start():
    """Called before executing a SQL statement."""
    _sql_start_var.set(time.perf_counter())


def record_sql_end():
    """Called after executing a SQL statement."""
    start = _sql_start_var.get()
    if start > 0:
        elapsed = (time.perf_counter() - start) * 1000.0
        _sql_time_var.set(_sql_time_var.get() + elapsed)
        _query_count_var.set(_query_count_var.get() + 1)
        _sql_start_var.set(0.0)


class ProfilerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Reset contextvars for this request
        _query_count_var.set(0)
        _sql_time_var.set(0.0)
        _sql_start_var.set(0.0)

        start_time = time.perf_counter()

        response = await call_next(request)

        total_duration_ms = (time.perf_counter() - start_time) * 1000.0
        sql_duration_ms = _sql_time_var.get()
        query_count = _query_count_var.get()

        # Attach telemetry headers
        response.headers["X-Response-Time-Ms"] = f"{total_duration_ms:.2f}"
        response.headers["X-Query-Count"] = str(query_count)
        response.headers["X-SQL-Time-Ms"] = f"{sql_duration_ms:.2f}"

        method = request.method
        path = request.url.path
        status_code = response.status_code

        # Skip non-API routes or WebSocket pings from verbose logging
        if path.startswith("/api/") and not path.startswith("/api/health"):
            if total_duration_ms > 200.0:
                print(
                    f"\033[93m[PERF SLOW] {method} {path} | Status: {status_code} | "
                    f"Queries: {query_count} | SQL: {sql_duration_ms:.1f}ms | Total: {total_duration_ms:.1f}ms\033[0m"
                )
            else:
                print(
                    f"\033[92m[PERF] {method} {path} | Status: {status_code} | "
                    f"Queries: {query_count} | SQL: {sql_duration_ms:.1f}ms | Total: {total_duration_ms:.1f}ms\033[0m"
                )

        return response
