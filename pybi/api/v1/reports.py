"""FastAPI router for Report View layouts, data queries and visual exports."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from pybi.core.report_storage import (
    build_visual_data,
    list_report_tables,
    load_report_layout,
    query_distinct_values,
    query_table_data,
    rows_to_csv,
    rows_to_xlsx,
    save_report_layout,
)
from pybi.core.storage import default_storage
from pybi.models.report import ReportLayout

router = APIRouter(prefix="/api/v1/projects/{project_id}/report", tags=["Report View"])


class VisualDataRequest(BaseModel):
    """Request payload for executing the data query behind a visual."""

    widget: Dict[str, Any] = Field(description="Serialized VisualWidget")
    filters: List[Dict[str, Any]] = Field(default_factory=list, description="Page/report/cross filters")


class ReportExportRequest(BaseModel):
    """Request payload for downloading aggregated visual data."""

    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    format: str = Field("csv", description="csv or xlsx")
    filename: Optional[str] = None


def _require_project(project_id: str) -> None:
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")


@router.get("", response_model=ReportLayout)
async def get_report_layout(project_id: str) -> ReportLayout:
    """Return the saved report layout (or a fresh single-page report)."""
    _require_project(project_id)
    return load_report_layout(project_id)


@router.put("", response_model=ReportLayout)
async def put_report_layout(project_id: str, layout: ReportLayout) -> ReportLayout:
    """Persist the full report layout: pages, visuals, filters and theme."""
    _require_project(project_id)
    return save_report_layout(project_id, layout)


@router.get("/tables", response_model=List[Dict[str, Any]])
async def get_report_tables(project_id: str) -> List[Dict[str, Any]]:
    """Return semantic tables, columns, measures and any extra project files."""
    _require_project(project_id)
    return list_report_tables(project_id)


@router.get("/tables/{table_name}/data", response_model=Dict[str, Any])
async def get_report_table_data(
    project_id: str,
    table_name: str,
    limit: int = Query(5000, ge=1, le=100000),
    offset: int = Query(0, ge=0),
    sort_by: Optional[str] = None,
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """Paginated table data used by the Data View virtual grid."""
    _require_project(project_id)
    try:
        return query_table_data(
            project_id,
            table_name,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_dir=sort_dir,
            search=search,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unable to load table data: {exc}") from exc


@router.get("/tables/{table_name}/values", response_model=List[Any])
async def get_report_distinct_values(
    project_id: str,
    table_name: str,
    column: str,
    limit: int = Query(500, ge=1, le=5000),
    search: Optional[str] = None,
) -> List[Any]:
    """Return distinct values for a table column (filters and slicers)."""
    _require_project(project_id)
    try:
        return query_distinct_values(project_id, table_name, column, limit=limit, search=search)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unable to load values: {exc}") from exc


@router.post("/visual-data", response_model=Dict[str, Any])
async def get_report_visual_data(project_id: str, request: VisualDataRequest) -> Dict[str, Any]:
    """Execute the aggregation query backing a canvas visual."""
    _require_project(project_id)
    try:
        return build_visual_data(project_id, request.widget, extra_filters=request.filters)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Visual query failed: {exc}") from exc


@router.post("/export")
async def export_report_visual_data(project_id: str, request: ReportExportRequest) -> Response:
    """Download visual data as CSV or XLSX."""
    _require_project(project_id)
    export_format = (request.format or "csv").lower()
    base_name = re.sub(r"[^A-Za-z0-9_-]+", "_", request.filename or "report_visual").strip("_") or "report_visual"

    if export_format == "xlsx":
        content = rows_to_xlsx(request.columns, request.rows, sheet_name=base_name)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{base_name}.xlsx"
    elif export_format == "csv":
        content = rows_to_csv(request.columns, request.rows)
        media_type = "text/csv; charset=utf-8"
        filename = f"{base_name}.csv"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="format must be 'csv' or 'xlsx'")

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
