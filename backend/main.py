"""Backend FastAPI application entry point for PyBI."""

from nicegui import app as nicegui_app
from pybi.api.main import app as fastapi_app, register_routers

# Register all API v1 routers
register_routers(nicegui_app)

app = fastapi_app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
