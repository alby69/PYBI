"""UI Schema definition and FastAPI endpoint router for Declarative Schema-Driven UI Engine."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/ui", tags=["ui_schema"])


class ComponentSchema(BaseModel):
    """Pydantic model describing a declarative UI component."""

    type: str = Field(description="Component type e.g., q-btn, q-card, custom:dashboard-grid")
    props: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Vue / Quasar props")
    text: Optional[str] = Field(default=None, description="Text content inside component")
    children: Optional[List["ComponentSchema"]] = Field(default=None, description="Nested child components")
    action: Optional[str] = Field(default=None, description="API action string e.g., api:POST:/api/etl/execute")
    dataBinding: Optional[str] = Field(default=None, description="Reactive state binding path")
    key: Optional[str] = Field(default=None, description="Unique key for Vue rendering")


ComponentSchema.model_rebuild()


class UISchema(BaseModel):
    """Pydantic model describing a complete page UI schema."""

    page: str = Field(description="Page identifier e.g., viewer, etl-editor")
    components: List[ComponentSchema] = Field(description="List of top-level component schemas")
    meta: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata dictionary")


def get_viewer_schema(project_id: Optional[str] = None) -> UISchema:
    """Generate UI schema for the public viewer page."""
    return UISchema(
        page="viewer",
        meta={"title": "PyBI Executive Viewer", "read_only": True},
        components=[
            ComponentSchema(
                type="q-toolbar",
                props={"class": "bg-primary text-white shadow-2 q-mb-md rounded-borders"},
                children=[
                    ComponentSchema(type="q-toolbar-title", text="🚀 Executive Sales Dashboard (Viewer)"),
                    ComponentSchema(
                        type="q-chip",
                        props={"color": "positive", "textColor": "white", "icon": "lock", "dense": True},
                        text="READ ONLY",
                    ),
                ],
            ),
            ComponentSchema(
                type="q-card",
                props={"flat": True, "bordered": True, "class": "q-pa-md q-mb-md bg-grey-1"},
                children=[
                    ComponentSchema(
                        type="div",
                        props={"class": "row items-center q-gutter-md"},
                        children=[
                            ComponentSchema(
                                type="q-select",
                                props={
                                    "outlined": True,
                                    "dense": True,
                                    "label": "Select Project",
                                    "options": ["default", "demo_project"],
                                    "style": "min-width: 200px",
                                },
                                dataBinding="state:viewer.selectedProject",
                            ),
                            ComponentSchema(
                                type="q-select",
                                props={
                                    "outlined": True,
                                    "dense": True,
                                    "label": "Select Dashboard",
                                    "options": ["default_dashboard"],
                                    "style": "min-width: 200px",
                                },
                                dataBinding="state:viewer.selectedDashboard",
                            ),
                        ],
                    )
                ],
            ),
            ComponentSchema(
                type="custom:dashboard-grid",
                props={"isDraggable": False, "isResizable": False, "colNum": 12, "rowHeight": 60},
                dataBinding="state:viewer.layout",
            ),
        ],
    )


def get_etl_editor_schema() -> UISchema:
    """Generate UI schema for the ETL Editor page."""
    return UISchema(
        page="etl-editor",
        meta={"title": "ETL Pipeline Editor"},
        components=[
            ComponentSchema(
                type="q-toolbar",
                props={"class": "bg-dark text-white q-mb-md"},
                children=[
                    ComponentSchema(type="q-toolbar-title", text="⚡ ETL Pipeline Editor"),
                    ComponentSchema(
                        type="q-btn",
                        props={"label": "Execute Pipeline", "icon": "play_arrow", "color": "positive", "dense": True},
                        action="api:POST:/api/etl/execute",
                    ),
                ],
            ),
            ComponentSchema(
                type="custom:flow-editor",
                props={"height": "500px"},
                dataBinding="state:etl.dag",
            ),
        ],
    )


@router.get("/schema/{page_name}", response_model=UISchema)
def get_page_ui_schema(page_name: str, project_id: Optional[str] = None) -> UISchema:
    """FastAPI endpoint returning JSON UI schema for dynamic frontend rendering."""
    page_key = page_name.lower().strip()
    if page_key in ["viewer", "public-viewer"]:
        return get_viewer_schema(project_id)
    elif page_key in ["etl-editor", "etl_editor"]:
        return get_etl_editor_schema()
    else:
        return UISchema(
            page=page_key,
            components=[
                ComponentSchema(
                    type="q-banner",
                    props={"class": "bg-primary text-white q-mb-md"},
                    text=f"Page: {page_name}",
                )
            ],
        )
