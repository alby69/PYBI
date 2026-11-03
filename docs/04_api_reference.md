# 📚 PyBI REST API v1 Reference

## 1. Projects API
- `GET /api/v1/projects` — List available projects
- `POST /api/v1/projects` — Create new project
- `GET /api/v1/projects/{project_id}` — Get project metadata
- `PUT /api/v1/projects/{project_id}` — Update project metadata
- `DELETE /api/v1/projects/{project_id}` — Delete project

## 2. Semantic Model API
- `GET /api/v1/projects/{project_id}/semantic` — Fetch the model, including tables, relationships, measures, and canvas positions
- `PUT /api/v1/projects/{project_id}/semantic` — Replace and persist the complete model
- `GET /api/v1/projects/{project_id}/semantic/tables` — List model tables and columns
- `POST /api/v1/projects/{project_id}/semantic/relationships` — Create or update one relationship
- `PUT /api/v1/projects/{project_id}/semantic/relationships` — Replace the complete relationship list
- `DELETE /api/v1/projects/{project_id}/semantic/relationships/{rel_id}` — Delete one relationship
- `POST /api/v1/projects/{project_id}/semantic/relationships/autodetect` — Propose relationships from the current model (`POST /autodetect` is a compatibility alias)
- `POST /api/v1/projects/{project_id}/semantic/measures` — Create or update a calculated measure
- `POST /api/v1/projects/{project_id}/semantic/parameters` — Fetch distinct parameter values with optional parent filters

## 3. ETL Pipeline API
- `GET /api/v1/projects/{project_id}/etl/query` — Get saved linear ETL query
- `PUT /api/v1/projects/{project_id}/etl/query` — Save linear ETL query
- `POST /api/v1/projects/{project_id}/etl/execute` — Execute ETL pipeline
- `POST /api/v1/projects/{project_id}/etl/preview` — Preview step results

The Power Query page's header uploader accepts CSV, Parquet, JSON, SQLite, and
DB files. The `Get Data` ribbon command opens that same uploader.

## 4. Model Context Protocol (MCP) API
- `GET /api/v1/mcp/schema/{project_id}` — Get semantic schema
- `POST /api/v1/mcp/validate-dax` — Translate & validate DAX expression
- `POST /api/v1/mcp/execute-query` — Run analytical query
- `GET /api/v1/mcp/lineage/{project_id}` — Get data lineage
- `POST /api/v1/mcp/tools/{tool_name}` — Generic MCP tool invocation

## 5. Dashboards & Viewer API
- `GET /api/v1/projects/{project_id}/dashboards` — List dashboards
- `GET /api/v1/viewer/{project_id}/dashboards/{dashboard_id}/data` — Fetch read-only widget data
