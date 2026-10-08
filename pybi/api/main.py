"""FastAPI Application Wiring."""

from fastapi import FastAPI
from pybi.publish.viewer_api import router as viewer_router
from pybi.export_engine.router import router as export_router


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance."""
    app = FastAPI(title="PyBI Analytics API", version="0.1.0")
    app.include_router(viewer_router)
    app.include_router(export_router)
    return app


app = create_app()
