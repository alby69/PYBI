# 📚 PyBI REST API v1 Reference

## 1. Projects API
- `GET /api/v1/projects` — List available projects
- `POST /api/v1/projects` — Create new project
- `GET /api/v1/projects/{project_id}` — Get project metadata
- `PUT /api/v1/projects/{project_id}` — Update project metadata
- `DELETE /api/v1/projects/{project_id}` — Delete project

## 2. Semantic Model API
- `GET /api/v1/projects/{project_id}/semantic` — Fetch semantic model
- `PUT /api/v1/projects/{project_id}/semantic` — Update semantic model
- `PUT /api/v1/projects/{project_id}/semantic/relationships` — Update relationships
- `POST /api/v1/projects/{project_id}/semantic/autodetect` — Auto-detect table relationships

## 3. ETL Pipeline API
- `GET /api/v1/projects/{project_id}/etl/query` — Get saved linear ETL query
- `PUT /api/v1/projects/{project_id}/etl/query` — Save linear ETL query
- `POST /api/v1/projects/{project_id}/etl/execute` — Execute ETL pipeline
- `POST /api/v1/projects/{project_id}/etl/preview` — Preview step results

## 4. Model Context Protocol (MCP) API
- `GET /api/v1/mcp/schema/{project_id}` — Get semantic schema
- `POST /api/v1/mcp/validate-dax` — Translate & validate DAX expression
- `POST /api/v1/mcp/execute-query` — Run analytical query
- `GET /api/v1/mcp/lineage/{project_id}` — Get data lineage
- `POST /api/v1/mcp/tools/{tool_name}` — Generic MCP tool invocation

## 5. Dashboards & Viewer API
- `GET /api/v1/projects/{project_id}/dashboards` — List dashboards
- `GET /api/v1/viewer/{project_id}/dashboards/{dashboard_id}/data` — Fetch read-only widget data
