"""FastAPI router for Public Read-Only Viewer endpoints in PyBI v1 REST API."""

from typing import Any, Dict, List, Optional
import duckdb
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from pybi.core.storage import default_storage
from pybi.dashboard.binding import default_binder
import pybi.storage.project_manager as pm
from pybi.semantic.engine import SemanticQueryResolver
from pybi.semantic.models import SemanticQueryRequest, SemanticQueryResponse

router = APIRouter(prefix="/api/v1/viewer", tags=["Viewer"])


class TablixPreviewRequest(BaseModel):
    project_id: str = "default"
    table_name: str
    row_groups: List[str] = Field(default_factory=list)
    measures: List[Dict[str, Any]] = Field(default_factory=list)
    filter_context: Optional[Dict[str, Any]] = None


@router.get("/health")
def viewer_health() -> Dict[str, str]:
    """Health check endpoint for viewer API."""
    return {"status": "ok", "service": "pybi-viewer-api"}


@router.get("/projects/{project_id}")
def get_published_project(project_id: str) -> Dict[str, Any]:
    """Fetch published dashboard layout and schema for read-only viewing."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    dashboards = pm.load_dashboard_layout(project_id)
    layout = dashboards.get("layout", [])

    return {
        "project_id": project_id,
        "status": "published",
        "layout": layout,
        "tables": default_binder.list_sources(),
    }


@router.get("/{project_id}/dashboards/{dashboard_id}/data")
def get_viewer_dashboard_data(project_id: str, dashboard_id: str) -> Dict[str, Any]:
    """Optimized read-only endpoint returning aggregated widget data ready for rendering."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    layout = default_storage.load_dashboard(project_id, dashboard_id)
    if layout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard '{dashboard_id}' not found in project '{project_id}'",
        )

    widget_data: List[Dict[str, Any]] = []
    registered_sources = set(default_binder.list_sources())

    for item in layout:
        w_id = item.get("i", "w")
        w_type = item.get("widget_type", "chart")
        config = item.get("config", {})

        data_entry = {
            "id": w_id,
            "type": w_type,
            "config": config,
            "rows": [],
            "columns": [],
        }

        tbl_name = config.get("table_name") or config.get("source_name")
        if tbl_name and tbl_name in registered_sources:
            try:
                df = default_binder.get_source_data(tbl_name)
                data_entry["columns"] = df.columns
                data_entry["rows"] = df.head(100).to_dicts()
            except Exception:
                pass

        widget_data.append(data_entry)

    return {
        "project_id": project_id,
        "dashboard_id": dashboard_id,
        "widgets": widget_data,
        "sources": default_binder.list_sources(),
    }


@router.post("/{project_id}/semantic-query", response_model=SemanticQueryResponse)
def execute_semantic_query(project_id: str, request: SemanticQueryRequest) -> SemanticQueryResponse:
    """Execute a semantic query against a project's registered data sources or semantic models."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    resolver = SemanticQueryResolver()
    source_name = request.source_table or request.model_name
    source_df = None

    if source_name and source_name in default_binder.list_sources():
        try:
            source_df = default_binder.get_source_data(source_name)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error loading source '{source_name}': {e}")

    try:
        response = resolver.execute(request, source_df=source_df)
        return response
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Semantic query execution failed: {e}")


@router.post("/reports/{report_id}/preview")
def get_report_tablix_preview(report_id: str, request: TablixPreviewRequest) -> Dict[str, Any]:
    """Execute dynamic GROUP BY ROLLUP aggregation in DuckDB for Tablix report previews."""
    tbl_name = request.table_name
    if tbl_name not in default_binder.list_sources():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Table source '{tbl_name}' not found")

    df = default_binder.get_source_data(tbl_name)
    con = duckdb.connect(":memory:")
    raw_df = df.to_pandas() if hasattr(df, "to_pandas") else df
    con.register("tbl_data", raw_df)

    groups_str = ", ".join(request.row_groups) if request.row_groups else ""

    measure_exprs = []
    for m in request.measures:
        col = m.get("col") or m.get("column")
        agg = (m.get("agg") or m.get("aggregator") or "SUM").upper()
        title = m.get("title") or f"{col}_{agg.lower()}"
        if col:
            measure_exprs.append(f"{agg}({col}) AS \"{title}\"")

    if not measure_exprs:
        measure_exprs.append("COUNT(*) AS row_count")

    where_clauses = []
    if request.filter_context:
        for f_col, f_val in request.filter_context.items():
            if isinstance(f_val, list) and f_val:
                vals_str = ", ".join(f"'{v}'" for v in f_val)
                where_clauses.append(f"{f_col} IN ({vals_str})")
            elif f_val is not None and str(f_val).strip() != "":
                where_clauses.append(f"{f_col} = '{f_val}'")

    where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    if groups_str:
        sql = f"SELECT {groups_str}, {', '.join(measure_exprs)} FROM tbl_data {where_str} GROUP BY ROLLUP({groups_str})"
    else:
        sql = f"SELECT {', '.join(measure_exprs)} FROM tbl_data {where_str}"

    try:
        res_df = con.execute(sql).df()
        return {
            "report_id": report_id,
            "table_name": tbl_name,
            "sql": sql,
            "row_count": len(res_df),
            "columns": list(res_df.columns),
            "data": res_df.to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Rollup preview failed: {e}")
