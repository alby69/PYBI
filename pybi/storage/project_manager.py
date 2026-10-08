"""SQLite and File-backed project management module for PyBI projects."""

import json
import os
import sqlite3
from typing import Any, Dict, List, Optional

from pybi.core.storage import default_storage, sanitize_project_id

DEFAULT_DB_PATH = os.path.join("pybi_data", "projects.db")


# ==========================================================
# Granular File/Default Storage API Functions
# ==========================================================

def list_projects() -> List[Dict[str, Any]]:
    """List summary details for all saved projects.

    Returns:
        List[Dict[str, Any]]: List of project metadata dictionaries.
    """
    pids = default_storage.list_projects()
    results = []
    for pid in pids:
        try:
            p = default_storage.load_project(pid)
            results.append({
                "id": pid,
                "project_id": pid,
                "name": p.get("name") or pid,
                "description": p.get("description"),
                "updated_at": p.get("updated_at"),
                "created_at": p.get("created_at"),
            })
        except Exception:
            results.append({"id": pid, "project_id": pid, "name": pid})
    return results


def create_project(name: str, project_id: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
    """Create a new project.

    Args:
        name: Project display name.
        project_id: Optional explicit project ID.
        description: Optional project description.

    Returns:
        Dict[str, Any]: Created project dictionary.
    """
    if not name or not name.strip():
        raise ValueError("Project name cannot be empty.")

    pid = sanitize_project_id(project_id or name)
    if default_storage.project_exists(pid):
        raise ValueError(f"Project with ID '{pid}' already exists.")

    saved = default_storage.save_project(
        project_id=pid,
        name=name.strip(),
        etl_dag={"nodes": [], "edges": []},
        dashboards=[],
    )
    if description:
        saved["description"] = description
    return saved


def get_project(project_id: str) -> Dict[str, Any]:
    """Get project configuration by project_id.

    Args:
        project_id: Project identifier.

    Returns:
        Dict[str, Any]: Loaded project configuration.
    """
    if not default_storage.project_exists(project_id):
        raise FileNotFoundError(f"Project '{project_id}' not found.")
    return default_storage.load_project(project_id)


def update_project(
    project_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Update project name or description.

    Args:
        project_id: Project identifier.
        name: Optional new display name.
        description: Optional new description.

    Returns:
        Dict[str, Any]: Updated project configuration.
    """
    existing = get_project(project_id)
    new_name = name if name is not None else existing.get("name", project_id)
    updated = default_storage.save_project(
        project_id=project_id,
        name=new_name,
        etl_dag=existing.get("etl_dag"),
        dashboards=existing.get("dashboards"),
    )
    if description is not None:
        updated["description"] = description
    return updated


def delete_project(project_id: str) -> bool:
    """Delete a project and its associated files.

    Args:
        project_id: Project identifier.

    Returns:
        bool: True if project was deleted.
    """
    return default_storage.delete_project(project_id)


def save_dag(project_id: str, dag: Dict[str, Any]) -> None:
    """Save ETL pipeline DAG for a project.

    Args:
        project_id: Project identifier.
        dag: ETL DAG dictionary containing nodes and edges.
    """
    default_storage.save_etl_dag(project_id, dag)


def load_dag(project_id: str) -> Dict[str, Any]:
    """Load ETL pipeline DAG for a project.

    Args:
        project_id: Project identifier.

    Returns:
        Dict[str, Any]: ETL DAG dictionary.
    """
    return default_storage.load_etl_dag(project_id)


def save_dashboard_layout(
    project_id: str,
    layout: Any,
    dashboard_id: str = "dash_1",
    name: str = "Main Dashboard",
    bindings: Optional[Dict[str, Any]] = None,
) -> None:
    """Save or update dashboard grid layout and bindings.

    Args:
        project_id: Project identifier.
        layout: List of layout widget items.
        dashboard_id: Dashboard identifier.
        name: Display name of dashboard.
        bindings: Optional widget bindings dictionary.
    """
    default_storage.save_dashboard(
        project_id=project_id,
        dashboard_id=dashboard_id,
        name=name,
        layout=layout,
    )


def load_dashboard_layout(project_id: str, dashboard_id: str = "dash_1") -> Dict[str, Any]:
    """Load dashboard layout and bindings for a project.

    Args:
        project_id: Project identifier.
        dashboard_id: Dashboard identifier.

    Returns:
        Dict[str, Any]: Dictionary containing 'layout' and 'bindings'.
    """
    layout = default_storage.load_dashboard(project_id, dashboard_id)
    if layout is None:
        return {"layout": [], "bindings": {}}
    return {"layout": layout, "bindings": {}}


def delete_dashboard(project_id: str, dashboard_id: str) -> bool:
    """Delete specific dashboard from a project.

    Args:
        project_id: Project identifier.
        dashboard_id: Dashboard identifier.

    Returns:
        bool: True if deleted.
    """
    return default_storage.delete_dashboard(project_id, dashboard_id)


# ==========================================================
# Legacy SQLite Storage Functions (Backward Compatibility)
# ==========================================================

def _get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Ensure parent directory exists and return SQLite connection."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            name TEXT PRIMARY KEY,
            dag TEXT,
            dashboard_layout TEXT,
            bindings TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    return conn


def save_project(
    name: str,
    dag: Optional[Dict[str, Any]] = None,
    dashboard_layout: Optional[Dict[str, Any]] = None,
    bindings: Optional[Dict[str, Any]] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> bool:
    """Save or update project pipeline, dashboard layout, and bindings into SQLite."""
    if not name or not name.strip():
        raise ValueError("Project name cannot be empty.")

    clean_name = name.strip()
    dag_json = json.dumps(dag if dag is not None else {"nodes": [], "edges": []})
    layout_json = json.dumps(dashboard_layout if dashboard_layout is not None else [])
    bindings_json = json.dumps(bindings if bindings is not None else {})

    conn = _get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO projects (name, dag, dashboard_layout, bindings, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                dag = excluded.dag,
                dashboard_layout = excluded.dashboard_layout,
                bindings = excluded.bindings,
                updated_at = CURRENT_TIMESTAMP
            """,
            (clean_name, dag_json, layout_json, bindings_json),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def load_project(name: str, db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """Load project pipeline, dashboard layout, and bindings from SQLite database."""
    if not name or not name.strip():
        raise ValueError("Project name cannot be empty.")

    clean_name = name.strip()
    conn = _get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name, dag, dashboard_layout, bindings, updated_at FROM projects WHERE name = ?",
            (clean_name,),
        )
        row = cur.fetchone()
        if not row:
            raise FileNotFoundError(f"Project '{clean_name}' not found in SQLite database at '{db_path}'")

        proj_name, dag_str, layout_str, bindings_str, updated_at = row
        return {
            "name": proj_name,
            "dag": json.loads(dag_str) if dag_str else {"nodes": [], "edges": []},
            "dashboard_layout": json.loads(layout_str) if layout_str else [],
            "bindings": json.loads(bindings_str) if bindings_str else {},
            "updated_at": updated_at,
        }
    finally:
        conn.close()


if __name__ == "__main__":
    print("Testing pybi/storage/project_manager.py standalone...")
    test_db = os.path.join("pybi_data", "test_projects.db")
    if os.path.exists(test_db):
        os.remove(test_db)

    sample_dag = {"nodes": [{"id": "n1", "type": "csv"}], "edges": []}
    sample_layout = [{"i": "w1", "x": 0, "y": 0, "w": 4, "h": 3}]
    sample_bindings = {"w1": {"source_name": "sales"}}

    saved = save_project("demo_proj", sample_dag, sample_layout, sample_bindings, db_path=test_db)
    assert saved is True
    print("Saved demo_proj to SQLite successfully.")

    loaded = load_project("demo_proj", db_path=test_db)
    assert loaded["name"] == "demo_proj"
    assert loaded["dag"] == sample_dag
    assert loaded["dashboard_layout"] == sample_layout
    assert loaded["bindings"] == sample_bindings
    print("Loaded demo_proj successfully from SQLite.")

    if os.path.exists(test_db):
        os.remove(test_db)
    print("pybi/storage/project_manager.py self-test passed!")
