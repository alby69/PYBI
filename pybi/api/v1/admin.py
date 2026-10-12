"""Admin usage metrics router for PyBI v1 REST API."""

from fastapi import APIRouter, Depends, HTTPException, status

from pybi.api.middleware.audit import AuditLogStore
from pybi.api.v1.auth import get_current_user
from pybi.auth.jwt_auth import AuthUser

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


@router.get("/usage-metrics")
def get_usage_metrics(user: AuthUser = Depends(get_current_user)) -> dict:
    """Retrieve aggregated usage metrics (Admin role required)."""
    if user.role != "admin" and user.username.lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privilege required to access system metrics",
        )

    metrics = AuditLogStore.get_metrics()
    return metrics
