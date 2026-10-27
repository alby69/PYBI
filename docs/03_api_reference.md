# 🔌 PyBI REST API Reference (`/api/v1`)

PyBI exposes a versioned, OpenAPI-compliant REST API under `/api/v1`.

## 1. Projects API (`/api/v1/projects`)

- `GET /` — List all available projects.
- `POST /` — Create a new project (`{"name": str, "project_id": str}`).
- `GET /{project_id}` — Get project details and metadata.
- `PUT /{project_id}` — Update project metadata.
- `DELETE /{project_id}` — Delete project.

## 2. ETL API (`/api/v1/projects/{project_id}/etl`)

- `GET /dag` — Fetch saved ETL pipeline DAG.
- `PUT /dag` — Save updated pipeline DAG (`{"nodes": [], "edges": []}`).
- `POST /execute` — Trigger background execution of the ETL pipeline.
- `GET /jobs/{job_id}` — Poll background job execution status.

### Supported Visual ETL Transformation Nodes
- **Row & Column Filtering/Selection:** `Filter`, `Select`, `GroupBy`, `Join`, `CalculatedColumn`
- **Power Query Shaping & Transformations:**
  - `Unpivot` (`unpivot`): Unpivot attribute columns into name/value rows.
  - `FillDown` (`fill_down`): Forward-fill missing NULL values along ordered rows.
  - `RenameColumn` (`rename_column`): Rename columns with mapping dictionary.
  - `CastColumn` (`cast_column`): Cast data types (text, int, float, boolean, date, timestamp).
  - `SplitColumn` (`split_column`): Split text column by delimiter.
  - `TextTransform` (`text_transform`): Trim, Upper, Lower, Clean text.
  - `Deduplicate` (`deduplicate`): Remove duplicate rows.
  - `ConditionalColumn` (`conditional_column`): If-Then-Else conditional column generation.
  - `IndexColumn` (`index_column`): Row index generation.

## 3. Dashboards API (`/api/v1/projects/{project_id}/dashboards`)

- `GET /` — List dashboards in project.
- `POST /` — Create a new dashboard layout.
- `GET /{dashboard_id}` — Get layout configuration and widget bindings.
- `PUT /{dashboard_id}` — Save dashboard layout configuration.
- `DELETE /{dashboard_id}` — Delete dashboard layout.

## 4. Semantic API (`/api/v1/viewer/{project_id}/semantic-query`)

- `POST /` — Execute semantic query against registered semantic model.
  ```json
  {
    "model_name": "sales_enterprise_model",
    "dimensions": ["stores.country"],
    "measures": ["sales.total_revenue"],
    "filters": {"sales.region": "Europe"}
  }
  ```

## 5. Export API (`/api/v1/projects/{project_id}/export`)

- `POST /` — Initiate background export job (PDF, HTML, Markdown, CSV).
- `GET /api/v1/exports/{export_id}/status` — Poll export job status.
- `GET /api/v1/exports/{export_id}/download` — Download generated artifact.
