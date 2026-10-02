"""SQLite-backed project management module for saving and loading PyBI projects."""

import json
import os
import sqlite3
from typing import Any, Dict, Optional

DEFAULT_DB_PATH = os.path.join("pybi_data", "projects.db")


def _get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Ensure parent directory exists and return SQLite connection.

    Args:
        db_path: Path to SQLite database file.

    Returns:
        sqlite3.Connection: Database connection instance.
    """
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
    """Save or update project pipeline, dashboard layout, and bindings into SQLite.

    Args:
        name: Unique project name identifier.
        dag: Dict representing ETL DAG (nodes and edges).
        dashboard_layout: Dict or List representing dashboard layout.
        bindings: Dict representing DataBinder widget bindings.
        db_path: Optional path to SQLite database file.

    Returns:
        bool: True if project saved successfully.
    """
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
    """Load project pipeline, dashboard layout, and bindings from SQLite database.

    Args:
        name: Unique project name identifier.
        db_path: Optional path to SQLite database file.

    Returns:
        Dict[str, Any]: Project configuration dictionary containing 'name', 'dag',
            'dashboard_layout', and 'bindings'.

    Raises:
        FileNotFoundError: If no project with given name exists in database.
    """
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
    # Manual standalone test
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
