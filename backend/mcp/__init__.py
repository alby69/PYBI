"""Compatibility exports for the canonical MCP package."""

from pybi.mcp_integration import (
    execute_analytical_query,
    get_data_lineage,
    get_semantic_schema,
    mcp,
    validate_dax_expression,
)

__all__ = [
    "mcp",
    "execute_analytical_query",
    "get_data_lineage",
    "get_semantic_schema",
    "validate_dax_expression",
]
