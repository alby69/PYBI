"""Observability and Audit Logging Middleware for FastAPI REST API."""

import logging
import time
from typing import Any, Dict, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = logging.getLogger(__name__)


class AuditLogStore:
    """In-memory store for audit logs and system usage metrics."""

    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def log_request(self, method: str, path: str, status_code: int, duration_ms: float, client_ip: str):
        """Record an API request entry."""
        entry = {
            "timestamp": time.time(),
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": client_ip,
        }
        self.logs.append(entry)
        if len(self.logs) > 1000:
            self.logs.pop(0)

    def get_metrics(self) -> Dict[str, Any]:
        """Compute aggregated usage metrics."""
        total_requests = len(self.logs)
        status_counts: Dict[int, int] = {}
        total_ms = 0.0

        for entry in self.logs:
            sc = entry["status_code"]
            status_counts[sc] = status_counts.get(sc, 0) + 1
            total_ms += entry["duration_ms"]

        avg_latency_ms = round(total_ms / total_requests, 2) if total_requests > 0 else 0.0

        return {
            "total_requests": total_requests,
            "status_code_counts": status_counts,
            "average_latency_ms": avg_latency_ms,
            "recent_logs": self.logs[-20:],
        }


audit_store = AuditLogStore()


class AuditMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware capturing access, response codes, and query timing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000.0
        audit_store.log_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=client_ip,
        )

        return response
