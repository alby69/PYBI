"""MCP Server implementation for PyBI Model Context Protocol integration."""

import logging
from typing import Any, Dict

from backend.mcp.tools import (
    execute_analytical_query as _execute_analytical_query,
    get_data_lineage as _get_data_lineage,
    get_semantic_schema as _get_semantic_schema,
    validate_dax_expression as _validate_dax_expression,
)

log = logging.getLogger(__name__)

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:
    try:
        from mcp.server.mcpserver import MCPServer as FastMCP
    except ImportError:
        class FastMCP:  # Fallback custom server if mcp SDK is absent
            def __init__(self, name: str):
                self.name = name
                self._tools = {}

            def tool(self, name: str = None):
                def decorator(func):
                    tool_name = name or func.__name__
                    self._tools[tool_name] = func
                    return func
                return decorator


# Initialize MCP Server instance
mcp = FastMCP("PyBI Semantic Engine")


@mcp.tool()
def get_semantic_schema(project_id: str = "default") -> str:
    """Restituisce lo schema semantico (tabelle, misure, relazioni) per aiutare l'IA a formulare query."""
    return _get_semantic_schema(project_id)


@mcp.tool()
def translate_and_validate_dax(dax_expression: str, project_id: str = "default") -> Dict[str, Any]:
    """Traduce una misura DAX in SQL DuckDB e ne valida la correttezza."""
    return _validate_dax_expression(dax_expression, project_id)


@mcp.tool()
def execute_analytical_query(query: str, project_id: str = "default", limit: int = 100) -> Dict[str, Any]:
    """Esegue una query DAX o SQL sul motore DuckDB, restituendo i risultati in formato tabellare."""
    return _execute_analytical_query(query, project_id, limit)


@mcp.tool()
def get_data_lineage(project_id: str = "default") -> Dict[str, Any]:
    """Restituisce la provenienza dei dati e le trasformazioni ETL applicate per governance ed etica AI."""
    return _get_data_lineage(project_id)
