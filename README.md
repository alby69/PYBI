# 🔍 OpenBI / PyBI - Python Business Intelligence Platform

**PyBI** (Python Business Intelligence) is an open-source, 100% Python-based BI platform designed as a modern alternative to PowerBI Desktop.

---

## 🏗️ Architecture & Stack (Phase 0 Foundation)

- **Frontend Core:** [NiceGUI](https://nicegui.io/) (Python framework built on Vue 3 & Quasar)
- **ETL Visual Canvas:** [Vue Flow (`@vue-flow/core`)](https://vueflow.dev/) wrapped as a custom NiceGUI `ui.element`
- **Dashboard Grid Canvas:** [Vue Grid Layout (`grid-layout-plus`)](https://grid-layout-plus.netlify.app/) wrapped as a custom NiceGUI `ui.element`
- **Analytical Engine:** DuckDB + Polars
- **API & Server:** FastAPI + Uvicorn
- **Auth & RBAC:** Casbin + PyJWT

---

## 🐳 Docker Deployment (Phase 1)

The simplest way to run PyBI is using Docker and Docker Compose.

> **Prerequisite:** Docker and Docker Compose must be installed and running on your system.

### Linux / macOS
1. Make the start and stop scripts executable (first time only):
   ```bash
   chmod +x start.sh stop.sh
   ```
2. Start the application:
   ```bash
   ./start.sh
   ```
3. Access PyBI in your browser at: [http://localhost:8080](http://localhost:8080)
4. Stop the application:
   ```bash
   ./stop.sh
   ```

### Windows
1. Start the application by double-clicking `start.bat` or running in Command Prompt / PowerShell:
   ```cmd
   start.bat
   ```
2. Access PyBI in your browser at: [http://localhost:8080](http://localhost:8080)
3. Stop the application by double-clicking `stop.bat` or running:
   ```cmd
   stop.bat
   ```

---

## 🚀 Quickstart & Setup (Local Python)

### 1. Installation
```bash
pip install -e .
```

Or install directly from `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 2. Launching the Application
Launch via python module:
```bash
python3 -m pybi.main
```

Or run via installed CLI command:
```bash
pybi --port 8080 --host 0.0.0.0
```

---

## 🌐 Routes & Features

- **`/` (Home):** Welcome dashboard & portal navigation.
- **`/etl-editor` (ETL DAG Editor):**
  - Interactive pipeline canvas powered by Vue Flow.
  - **Node palette:** add Data Source, Filter Rows, Select Columns, Group By, Join Tables and Output Table nodes.
  - **Property editor:** double-click a node to edit its parameters, or delete it.
  - Pipeline validation before execution (missing connections, cycles).
  - Reactive `nodes` and `edges` state synced bidirectionally between Python and Vue frontend.
  - Event listeners for node selection (`node_click`, `node_dbl_click`), repositioning
    (`node_drag_stop`), connection creation (`connect`) and pipeline modifications (`change`).
- **`/dashboard-editor` (Dashboard Editor):**
  - Drag-and-drop & resizable widget grid powered by Vue Grid Layout.
  - Supports KPI cards, bar charts, data tables, and custom cards.
  - Real-time layout updates emitted to Python backend.
- **`/viewer` (Public Read-Only Viewer):**
  - Read-only dashboard view (`is_draggable=False`, `is_resizable=False`) for end-user consultation.

---

## 🗂️ Projects

A project bundles an ETL pipeline and a dashboard layout. Each project is a single
JSON file in `pybi_data/projects/<project_id>.json`, managed from the project
selector in the ETL Editor and Dashboard Editor (switch, create, rename, delete).

The storage directory is resolved in this order: explicit argument, the `DATA_DIR`
environment variable, then `pybi_data`. In Docker `DATA_DIR=/app/data` points at the
`./pybi_data` bind mount, so projects survive container rebuilds.

`etl_dag` and `dashboard_layout` are saved independently: saving a pipeline never
overwrites the dashboard layout and vice versa. Switching projects reloads both.

Project ids are sanitized to filesystem-safe names (alphanumerics, `-` and `_` only),
so `my project` is stored as `myproject.json`.

---

## 🧩 Node Reference

Nodes are executed by `pybi/etl/executor.py`; the canonical templates live in
`pybi/etl/node_factory.py`. Each node stores its parameters under `data`:

| Node | Parameters | Notes |
|---|---|---|
| **Data Source** | `source_type` (`csv`/`parquet`/`sqlite`), `file_path`, `query` | `query` is SQLite only: a `SELECT`/`WITH` statement, a table name, or empty for the first table |
| **Filter Rows** | `condition` | DuckDB `WHERE` expression; use single quotes for strings, e.g. `region = 'EU'` |
| **Select Columns** | `columns` | Comma separated column names |
| **Group By** | `group_by`, `aggregations` | `aggregations` uses `column:function` pairs, e.g. `sales:sum` |
| **Join Tables** | `left_on`, `right_on`, `how` | Needs two inputs. `how` is `inner`, `left`, `right`, `full`, `cross`, `semi` or `anti` |
| **Output Table** | `table_name`, `output_type` (`duckdb`/`sqlite`), `file_path` | `duckdb` keeps the table in memory and exposes it to dashboard widgets; `sqlite` also writes a database file |

Nodes are executed in topological order. Each node reads its first input, except the
**Join Tables** node, which reads exactly two: the first connection is the left table
and the second one is the right table. Output tables are registered in the shared
`default_binder` (in memory), so the Dashboard Editor sees them after you run a
pipeline in the same server session.

---

## 🧪 Testing & Verification

Unit and end-to-end tests require `pytest` and `playwright` with a Chromium install:
```bash
pip install pytest playwright
playwright install --with-deps chromium
python3 -m pytest tests/ -q
```

Inside Docker, mount the tests folder (the image excludes them):
```bash
docker compose run --rm -v "$PWD/tests:/app/tests" pybi \
  sh -c "pip install pytest playwright && playwright install --with-deps chromium && python -m pytest tests/ -q"
```

---

## 🌁 Vue-Python Bridge Architecture

NiceGUI's `ui.element` is extended with custom JS files (`flow_editor.js` and `dashboard_grid.js`).
Since NiceGUI provides an ES importmap mapping `"vue"` to NiceGUI's internal Vue 3 instance, importing libraries (`@vue-flow/core` and `grid-layout-plus`) directly via browser ESM preserves a single, unified Vue context with zero duplicate library overhead.
Events emitted from Vue (`$emit`) automatically trigger registered Python callback handlers in real time.
