# 🔌 Model Context Protocol (MCP) & AI Integration

## 1. Overview
PyBI implements native Model Context Protocol (MCP) server endpoints (`backend/mcp`), enabling LLM agents (Claude Desktop, Cursor, ChatGPT, Qwen, DeepSeek) to interact with the semantic model without hallucinating schemas or business rules.

---

## 2. Exposed MCP Tools

1. **`get_semantic_schema(project_id: str)`**
   - Returns complete model schema (tables, columns, measures, relationships) as compact JSON.
2. **`translate_and_validate_dax(dax_expression: str, project_id: str)`**
   - Validates DAX expressions using `DaxEngine` and returns translated DuckDB SQL syntax or errors.
3. **`execute_analytical_query(query: str, project_id: str, limit: int)`**
   - Safely executes DAX/SQL queries against project DuckDB engine with configurable row limits.
4. **`get_data_lineage(project_id: str)`**
   - Exposes raw data source provenance and applied ETL steps for ethical data governance.

---

## 3. Configuration with Claude Desktop / Cursor

Add the following configuration to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pybi-semantic-engine": {
      "command": "python3",
      "args": ["-m", "backend.mcp.server"]
    }
  }
}
```

---

## 4. REST API Endpoints for MCP
- `GET /api/v1/mcp/schema/{project_id}`
- `POST /api/v1/mcp/validate-dax`
- `POST /api/v1/mcp/execute-query`
- `GET /api/v1/mcp/lineage/{project_id}`
- `POST /api/v1/mcp/tools/{tool_name}`
