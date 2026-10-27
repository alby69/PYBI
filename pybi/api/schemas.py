"""Pydantic request and response schemas for PyBI REST API."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Payload for creating a new project."""

    name: str = Field(description="Human readable project name")
    project_id: Optional[str] = Field(default=None, description="Optional explicit project identifier")
    description: Optional[str] = Field(default=None, description="Optional project description")


class ProjectResponse(BaseModel):
    """Full project response schema."""

    id: str = Field(description="Unique project identifier")
    name: str = Field(description="Human readable project name")
    updated_at: Optional[str] = Field(default=None, description="ISO timestamp of last update")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp of creation")
    description: Optional[str] = Field(default=None, description="Project description")
    etl_dag: Dict[str, Any] = Field(default_factory=dict, description="ETL DAG configuration")
    dashboards: List[Dict[str, Any]] = Field(default_factory=list, description="List of dashboards")
    dashboard_layout: Optional[Any] = Field(default=None, description="Primary dashboard layout")


class ETLStep(BaseModel):
    """Linear ETL step representation for Applied Steps pipeline."""

    id: str = Field(description="Unique step identifier")
    name: str = Field(description="Display step name (e.g., 'Righe filtrate')")
    operation: str = Field(description="Operation type (e.g. filter, cast_column, add_column)")
    params: Dict[str, Any] = Field(default_factory=dict, description="Operation configuration parameters")


class ETLQuery(BaseModel):
    """Linear ETL Query representation containing source definition and sequential steps."""

    query_name: str = Field(default="Sales_Data", description="Human readable query name")
    source: Dict[str, Any] = Field(default_factory=dict, description="Source definition dictionary")
    steps: List[ETLStep] = Field(default_factory=list, description="Sequential list of applied ETL steps")


class DagSaveRequest(BaseModel):
    """Payload for saving an ETL pipeline DAG or linear Query."""

    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="List of DAG nodes")
    edges: List[Dict[str, Any]] = Field(default_factory=list, description="List of DAG edges")
    query_name: Optional[str] = Field(default=None, description="Optional linear query name")
    source: Optional[Dict[str, Any]] = Field(default=None, description="Optional linear source definition")
    steps: Optional[List[ETLStep]] = Field(default=None, description="Optional linear ETL steps")


class DashboardCreateRequest(BaseModel):
    """Payload for creating a new dashboard."""

    name: str = Field(description="Display name for the new dashboard")


class DashboardSaveRequest(BaseModel):
    """Payload for saving or updating a dashboard layout and bindings."""

    name: Optional[str] = Field(default=None, description="Dashboard display name")
    layout: List[Dict[str, Any]] = Field(default_factory=list, description="Grid layout items list")
    bindings: Dict[str, Any] = Field(default_factory=dict, description="Widget data bindings dictionary")


class JobStatusResponse(BaseModel):
    """Response model for ETL execution background job status polling."""

    job_id: str = Field(description="Unique job execution identifier")
    status: str = Field(description="Job status: running | success | error")
    logs: List[str] = Field(default_factory=list, description="Execution execution logs")
    output_tables: List[str] = Field(default_factory=list, description="Names of registered output tables")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")


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
