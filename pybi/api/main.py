"""FastAPI Application Wiring for PyBI REST API."""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pybi.api.v1.auth import router as v1_auth_router
from pybi.api.v1.projects import router as v1_projects_router
from pybi.api.v1.files import router as v1_files_router
from pybi.api.v1.etl import router as v1_etl_router
from pybi.api.v1.dashboards import router as v1_dashboards_router
from pybi.api.v1.exports import router as v1_exports_router
from pybi.api.v1.ui_schema import router as v1_ui_schema_router
from pybi.api.v1.viewer import router as v1_viewer_router

# Legacy routes for backward compatibility
from pybi.publish.viewer_api import router as viewer_router
from pybi.export.router import router as export_router
from pybi.server.ui_schema import router as ui_schema_router


def create_app() -> FastAPI:
    """Create and configure pure FastAPI application instance with API v1 routes."""
    app = FastAPI(
        title="PyBI Analytics API",
        version="1.0.0",
        description="Pure Decoupled API-First REST Server for PyBI (Python Business Intelligence Platform)",
        openapi_tags=[
            {"name": "Auth", "description": "Authentication and user session management"},
            {"name": "Projects", "description": "Project management, storage, and file upload operations"},
            {"name": "Files", "description": "Data source file management for projects"},
            {"name": "ETL", "description": "ETL pipeline DAG definition, execution, and data preview"},
            {"name": "Dashboards", "description": "Interactive dashboard layout grid and widget operations"},
            {"name": "Exports", "description": "Async multi-format export and snapshot generation"},
            {"name": "UI Schema", "description": "Declarative Schema-Driven UI rendering specification"},
            {"name": "Viewer", "description": "Read-only published dashboard viewing endpoints"},
        ],
    )

    # Configure strict CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global standardized JSON exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        if hasattr(exc, "status_code"):
            status_code = getattr(exc, "status_code")
            detail = getattr(exc, "detail", str(exc))
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            detail = str(exc) or "Internal Server Error"

        return JSONResponse(
            status_code=status_code,
            content={"detail": detail, "code": "API_ERROR"},
        )

    # Include versioned v1 REST API routers
    app.include_router(v1_auth_router)
    app.include_router(v1_projects_router)
    app.include_router(v1_files_router)
    app.include_router(v1_etl_router)
    app.include_router(v1_dashboards_router)
    app.include_router(v1_exports_router)
    app.include_router(v1_ui_schema_router)
    app.include_router(v1_viewer_router)

    # Include legacy /api routes for backward compatibility with existing tests
    app.include_router(viewer_router)
    app.include_router(export_router)
    app.include_router(ui_schema_router)

    return app


app = create_app()
