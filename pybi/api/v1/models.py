"""Pydantic request and response models for PyBI REST API v1."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ==========================================
# Common & Error Models
# ==========================================

class ErrorResponse(BaseModel):
    """Standardized error response payload."""

    detail: str = Field(description="Human readable error message")
    code: str = Field(default="GENERAL_ERROR", description="Machine readable error code")


class MessageResponse(BaseModel):
    """Generic status/message response payload."""

    message: str = Field(description="Status or operation summary message")
    success: bool = Field(default=True, description="Indicates whether the operation succeeded")


# ==========================================
# Auth Models
# ==========================================

class LoginRequest(BaseModel):
    """User authentication login request."""

    username: str = Field(description="Username or user identifier")
    password: str = Field(description="User password")


class UserProfile(BaseModel):
    """Authenticated user profile info."""

    username: str = Field(description="Username")
    role: str = Field(default="viewer", description="User role (e.g. admin, editor, viewer)")
    email: Optional[str] = Field(default=None, description="Optional user email address")


class TokenResponse(BaseModel):
    """JWT Token authentication response."""

    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type prefix")
    user: UserProfile = Field(description="Authenticated user profile details")


# ==========================================
# Project Models
# ==========================================

class ProjectSummary(BaseModel):
    """Summary representation of a project."""

    project_id: str = Field(description="Unique project identifier")
    name: str = Field(description="Human readable project name")
    description: Optional[str] = Field(default=None, description="Project description")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp of creation")
    updated_at: Optional[str] = Field(default=None, description="ISO timestamp of last update")


class ProjectCreateRequest(BaseModel):
    """Payload for creating a new project."""

    project_id: str = Field(description="Unique project identifier")
    name: str = Field(description="Human readable project name")
    description: Optional[str] = Field(default=None, description="Project description")


class ProjectUpdateRequest(BaseModel):
    """Payload for updating an existing project."""

    name: Optional[str] = Field(default=None, description="Updated project name")
    description: Optional[str] = Field(default=None, description="Updated project description")


class ProjectResponse(BaseModel):
    """Full project configuration response."""

    project_id: str = Field(description="Unique project identifier")
    name: str = Field(description="Human readable project name")
    description: Optional[str] = Field(default=None, description="Project description")
    etl_dag: Dict[str, Any] = Field(default_factory=dict, description="ETL DAG configuration")
    dashboards: List[Dict[str, Any]] = Field(default_factory=list, description="List of dashboards")
    dashboard_layout: Optional[Any] = Field(default=None, description="Primary dashboard layout")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp of creation")
    updated_at: Optional[str] = Field(default=None, description="ISO timestamp of last update")


class ProjectListResponse(BaseModel):
    """Response containing a list of project summaries."""

    projects: List[ProjectSummary] = Field(default_factory=list, description="List of project summaries")
    total: int = Field(description="Total count of projects")


class FileUploadResponse(BaseModel):
    """Response returned when a data file is uploaded to a project."""

    filename: str = Field(description="Name of the saved file")
    file_path: str = Field(description="Absolute file path on server")
    size_bytes: int = Field(description="File size in bytes")
    message: str = Field(description="Confirmation message")


class FileListResponse(BaseModel):
    """List of data source files uploaded for a project."""

    project_id: str = Field(description="Project identifier")
    files: List[str] = Field(default_factory=list, description="List of filenames in project data folder")


# ==========================================
# ETL Models
# ==========================================

class ETLNodeSchema(BaseModel):
    """Representation of a node in an ETL Vue Flow DAG."""

    id: str = Field(description="Unique node identifier")
    type: Optional[str] = Field(default=None, description="Vue Flow node type identifier")
    label: Optional[str] = Field(default=None, description="Display label for node")
    position: Optional[Dict[str, Any]] = Field(default=None, description="Canvas x, y coordinates")
    data: Dict[str, Any] = Field(default_factory=dict, description="Node configuration parameters")


class ETLEdgeSchema(BaseModel):
    """Representation of an edge connecting two nodes in an ETL DAG."""

    id: str = Field(description="Unique edge identifier")
    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    sourceHandle: Optional[str] = Field(default=None, description="Optional source handle identifier")
    targetHandle: Optional[str] = Field(default=None, description="Optional target handle identifier")


class ETLDAGSchema(BaseModel):
    """Representation of an entire ETL pipeline DAG."""

    nodes: List[ETLNodeSchema] = Field(default_factory=list, description="List of DAG nodes")
    edges: List[ETLEdgeSchema] = Field(default_factory=list, description="List of DAG edges")


class SaveETLDAGRequest(BaseModel):
    """Payload for saving an ETL DAG for a project."""

    dag: ETLDAGSchema = Field(description="ETL DAG configuration to save")


class ETLExecuteRequest(BaseModel):
    """Payload for requesting execution of an ETL DAG."""

    project_id: Optional[str] = Field(default=None, description="Associated project ID")
    dag: Optional[ETLDAGSchema] = Field(default=None, description="Optional explicit DAG override")


class ETLExecuteResponse(BaseModel):
    """Execution output summary of an ETL DAG."""

    status: str = Field(description="Execution status: success | error")
    logs: List[str] = Field(default_factory=list, description="Execution execution logs")
    output_tables: List[str] = Field(default_factory=list, description="Names of registered output tables")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")


class ETLPreviewRequest(BaseModel):
    """Payload for previewing node data in an ETL pipeline."""

    project_id: Optional[str] = Field(default=None, description="Associated project ID")
    node_id: str = Field(description="Node ID to preview output for")
    limit: int = Field(default=100, description="Maximum number of rows to return")


class ETLPreviewResponse(BaseModel):
    """Preview output data for an ETL node."""

    node_id: str = Field(description="Node ID previewed")
    columns: List[str] = Field(default_factory=list, description="List of column names")
    rows: List[Dict[str, Any]] = Field(default_factory=list, description="Preview row records")
    total_rows: int = Field(description="Total rows in preview result")


# ==========================================
# Dashboard Models
# ==========================================

class DashboardItemSchema(BaseModel):
    """Individual widget element layout configuration within a grid layout."""

    i: str = Field(description="Widget item key/identifier")
    x: int = Field(description="Grid row position x")
    y: int = Field(description="Grid column position y")
    w: int = Field(description="Grid width w")
    h: int = Field(description="Grid height h")
    widget_type: Optional[str] = Field(default=None, description="Widget type (e.g. chart, pivot, kpi)")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Widget configuration parameters")


class DashboardSchema(BaseModel):
    """Dashboard layout representation."""

    id: str = Field(description="Dashboard ID")
    name: str = Field(description="Dashboard name")
    layout: List[Dict[str, Any]] = Field(default_factory=list, description="List of grid item configurations")


class SaveDashboardRequest(BaseModel):
    """Payload for saving or updating a dashboard layout."""

    name: Optional[str] = Field(default=None, description="Dashboard display name")
    layout: List[Dict[str, Any]] = Field(default_factory=list, description="Grid layout list")


class DashboardListResponse(BaseModel):
    """Response containing saved dashboards for a project."""

    project_id: str = Field(description="Project identifier")
    dashboards: List[DashboardSchema] = Field(default_factory=list, description="List of project dashboards")


# ==========================================
# Export Models
# ==========================================

class ExportRequest(BaseModel):
    """Payload model for project export requests."""

    format: str = Field(default="html", description="Export format: pdf | html | md | csv")
    template_id: Optional[str] = Field(default=None, description="Jinja2 template filename")
    filter_context: Optional[Dict[str, Any]] = Field(default=None, description="Active filter context rules")
    ai_compilation_prompt: Optional[str] = Field(default=None, description="Prompt for AI-assisted compilation")
    payload: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Export payload (widgets, tables, title)")


class ExportJobResponse(BaseModel):
    """Response returned when an async export job is created."""

    export_id: str = Field(description="Unique export job identifier")
    status: str = Field(description="Job status: pending | processing | completed | failed")
    message: str = Field(description="Status message")
    status_url: str = Field(description="URL to check job status")
    download_url: str = Field(description="URL to download generated artifact")
