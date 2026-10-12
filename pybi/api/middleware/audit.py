"""Audit logging middleware for FastAPI in PyBI."""

from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

log = logging.getLogger("pybi.audit")


class AuditLogStore:
    """In-memory audit log record store with summary metrics aggregation."""

    _logs: List[Dict[str, Any]] = []

    @classmethod
    def log_event(cls, event: Dict[str, Any]) -> None:
        """Record audit event."""
        cls._logs.append(event)

    @classmethod
    def get_logs(cls, limit: int = 100) -> List[Dict[str, Any]]:
        """Return recent log records."""
        return cls._logs[-limit:]

    @classmethod
    def get_metrics(cls) -> Dict[str, Any]:
        """Aggregate audit usage metrics."""
        total_requests = len(cls._logs)
        if total_requests == 0:
            return {
                "total_requests": 0,
                "active_users": 0,
                "avg_response_time_ms": 0.0,
                "project_queries": {},
                "status_codes": {},
            }

        users = {log_item["user_id"] for log_item in cls._logs if log_item.get("user_id")}
        durations = [log_item["duration_ms"] for log_item in cls._logs if "duration_ms" in log_item]
        avg_time = sum(durations) / len(durations) if durations else 0.0

        project_queries: Dict[str, int] = {}
        status_codes: Dict[int, int] = {}

        for l in cls._logs:
            p = l.get("project_id") or "global"
            project_queries[p] = project_queries.get(p, 0) + 1
            code = l.get("status_code", 200)
            status_codes[code] = status_codes.get(code, 0) + 1

        return {
            "total_requests": total_requests,
            "active_users": len(users),
            "avg_response_time_ms": round(avg_time, 2),
            "project_queries": project_queries,
            "status_codes": status_codes,
        }

    @classmethod
    def clear(cls) -> None:
        cls._logs.clear()


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware intercepting requests and logging structured audit metadata."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()

        # Determine user_id from auth header if present
        user_id = "anonymous"
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from pybi.auth.jwt_auth import decode_access_token
                token = auth_header.split(" ", 1)[1]
                payload = decode_access_token(token)
                if payload and "sub" in payload:
                    user_id = payload["sub"]
            except Exception:
                pass

        # Extract project ID if in URL path
        project_id = None
        path_parts = request.url.path.split("/")
        if "projects" in path_parts:
            idx = path_parts.index("projects")
            if idx + 1 < len(path_parts):
                project_id = path_parts[idx + 1]

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "method": request.method,
            "path": request.url.path,
            "project_id": project_id,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        }

        AuditLogStore.log_event(event)
        log.info(f"AUDIT: {event['method']} {event['path']} - {event['status_code']} ({event['duration_ms']}ms) by {event['user_id']}")

        return response
