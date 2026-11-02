"""Compatibility exports and entry point for the canonical MCP server."""

from pybi.mcp_integration.server import *
from pybi.mcp_integration.server import mcp


if __name__ == "__main__":
    mcp.run()
