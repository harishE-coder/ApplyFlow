"""
ApplyFlow Backend Performance & Query Profiler Middleware.
Provides real-time telemetry on every incoming API request:
- Route and HTTP method
- Server-side duration (in milliseconds)
- Status code
- Visual slow-query alerts for requests exceeding 200ms
"""

import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("applyflow.perf")
logging.basicConfig(level=logging.INFO)

class ProfilerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        
        # Process the request
        response = await call_next(request)
        
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        
        # Attach telemetry header
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        
        method = request.method
        path = request.url.path
        status_code = response.status_code
        
        # Skip noisy static assets or WebSocket pings from logging
        if path.startswith("/api/"):
            if duration_ms > 200.0:
                print(f"\033[93m[PERF SLOW ALERT] {method} {path} | Status: {status_code} | Total: {duration_ms:.1f}ms (>200ms threshold)\033[0m")
            else:
                print(f"\033[92m[PERF] {method} {path} | Status: {status_code} | Total: {duration_ms:.1f}ms\033[0m")
                
        return response
