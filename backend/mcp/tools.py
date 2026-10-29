"""MCP Tools for PyBI Semantic Model & AI Agent Integration."""

import json
import logging
from typing import Any, Dict, List, Optional

import duckdb
from backend.core.dax_engine import DaxEngine
from pybi.core.model_sync import load_project_semantic_model
from pybi.core.storage import default_storage

log = logging.getLogger(__name__)


def get_semantic_schema(project_id: str = "default") -> str:
    """Restituisce lo schema semantico (tabelle, colonne, misure, relazioni) per aiutare l'IA a formulare query."""
    try:
        model = load_project_semantic_model(project_id)
        schema_dict = {
            "model_name": model.name,
            "project_id": project_id,
            "tables": [
                {
                    "name": t.name,
                    "columns": [
                        {"name": c.name, "type": c.data_type, "is_key": c.is_key}
                        for c in t.columns
                    ],
                    "measures": [
                        {"name": m.name, "expression": m.expression, "label": m.label}
                        for m in t.measures
                    ],
                }
                for t in model.tables
            ],
            "relationships": [
                {
                    "from": f"{r.from_table}.{r.from_column}",
                    "to": f"{r.to_table}.{r.to_column}",
                    "cardinality": r.cardinality,
                    "is_active": r.is_active,
                }
                for r in model.relationships
            ],
        }
        return json.dumps(schema_dict, indent=2)
    except Exception as err:
        log.error("Error retrieving semantic schema for %s: %s", project_id, err)
        return json.dumps({"error": str(err)})


def validate_dax_expression(dax_expression: str, project_id: str = "default") -> Dict[str, Any]:
    """Traduce una misura/espressione DAX in SQL DuckDB e ne valida la correttezza."""
    try:
        model = load_project_semantic_model(project_id)
        sql = DaxEngine.translate(dax_expression, model)
        return {
            "status": "success",
            "dax_expression": dax_expression,
            "translated_sql": sql,
        }
    except Exception as err:
        return {"status": "error", "message": str(err)}


def execute_analytical_query(query: str, project_id: str = "default", limit: int = 100) -> Dict[str, Any]:
    """Esegue una query DAX o SQL sul motore DuckDB, restituendo i risultati in formato tabellare."""
    try:
        model = load_project_semantic_model(project_id)
        # Attempt translating if it looks like DAX or use raw query
        sql = query
        if not query.strip().upper().startswith("SELECT"):
            sql = f"SELECT {DaxEngine.translate(query, model)}"

        conn = duckdb.connect(":memory:")
        # Register sample data or files if available in project
        try:
            data_dir = default_storage.get_project_data_dir(project_id)
            for file in default_storage.list_project_files(project_id):
                if file.endswith(".csv"):
                    table_name = file.rsplit(".", 1)[0]
                    conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto('{data_dir}/{file}')")
        except Exception:
            pass

        # Apply safe limit
        safe_limit = min(max(1, limit), 500)
        if "LIMIT" not in sql.upper():
            sql += f" LIMIT {safe_limit}"

        res = conn.execute(sql)
        columns = [desc[0] for desc in res.description] if res.description else []
        rows = res.fetchall()

        return {
            "status": "success",
            "query": sql,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
        }
    except Exception as err:
        return {"status": "error", "message": str(err)}


def get_data_lineage(project_id: str = "default") -> Dict[str, Any]:
    """Restituisce la provenienza dei dati e le trasformazioni ETL applicate per governance ed etica AI."""
    try:
        dag = {}
        try:
            dag = default_storage.load_etl_dag(project_id) or {}
        except Exception:
            pass

        source = dag.get("source", {}) if isinstance(dag, dict) else {}
        steps = dag.get("steps", []) if isinstance(dag, dict) else []
        nodes = dag.get("nodes", []) if isinstance(dag, dict) else []

        lineage = {
            "project_id": project_id,
            "data_sources": [source] if source else [],
            "transformation_steps": [
                {
                    "step_index": idx,
                    "type": s.get("type", "unknown") if isinstance(s, dict) else getattr(s, "type", "unknown"),
                    "params": s.get("params", {}) if isinstance(s, dict) else getattr(s, "params", {}),
                }
                for idx, s in enumerate(steps)
            ],
            "dag_nodes": [
                {
                    "id": n.get("id") if isinstance(n, dict) else getattr(n, "id", None),
                    "type": n.get("type") if isinstance(n, dict) else getattr(n, "type", None),
                    "label": n.get("label") if isinstance(n, dict) else getattr(n, "label", None),
                }
                for n in nodes
            ],
        }

        return {"status": "success", "lineage": lineage}
    except Exception as err:
        return {"status": "error", "message": str(err)}
