# 🔍 OpenBI / PyBI - Python Business Intelligence Platform

[![CI/CD Pipeline](https://github.com/alby69/PYBI/actions/workflows/ci.yml/badge.svg)](https://github.com/alby69/PYBI/actions/workflows/ci.yml)

**PyBI** (Python Business Intelligence) is an open-source, 100% Python-based BI platform designed as a modern alternative to PowerBI Desktop, featuring a decoupled REST API architecture and Enterprise-grade analytical features.

---

## 🏛️ Architecture & Stack (Decoupled API-First Engine)

- **Backend (Pure REST API):** Pure FastAPI server exposing `/api/v1/` endpoints for Projects, ETL, Dashboards, Files, Exports, Semantic Queries, and Viewer with Pydantic schemas.
- **Frontend Core:** NiceGUI + Vue 3 & Quasar with **Declarative JSON-to-UI Engine (`DynamicRenderer`)** consuming REST APIs.
- **UI State Management:** Pinia / Vue Reactive Store (`uiStore.js`) fetching schemas from FastAPI (`/api/v1/ui/schema/{page_name}`)
- **ETL Visual Canvas:** [Vue Flow (`@vue-flow/core`)](https://vueflow.dev/) wrapped as a custom UI element
- **Dashboard Grid Canvas:** [Vue Grid Layout (`grid-layout-plus`)](https://grid-layout-plus.netlify.app/) wrapped as a custom UI element
- **Analytical Engine:** DuckDB + Polars
- **Connectors & Caching:** SQLAlchemy (Snowflake, BigQuery, Postgres, SQLite), Redis Query Cache
- **Publishing & Export Engine:** Headless Jinja2 + WeasyPrint / Async Worker Queue
- **Auth & RBAC:** Casbin + PyJWT

---

## 🏢 Enterprise Features

- **Semantic Model (`semantic_model.yaml`):** Multi-table relationship definitions (`1:1`, `1:*`, `*:1`), hierarchies, and calculated measures.
- **Dynamic Row-Level Security (RLS):** Contextual `WHERE` filter injection based on authenticated JWT claims (`allowed_regions`, `user_id`).
- **Enterprise Connectors & DirectQuery:** Live query execution on external databases (Snowflake, BigQuery, Postgres) via DuckDB secrets and SQLAlchemy.
- **ALM & Project Portability (`.pybi` Bundles):** Export and import full project bundles (layouts, ETL DAGs, semantic models, data) as `.pybi` packages.
- **Audit Logging & Observability:** Real-time access logging and usage metrics endpoint (`/api/v1/admin/usage-metrics`).

---

## 🛠️ API v1 Endpoint Specifications

PyBI exposes a complete versioned REST API under `/api/v1`:

- **Projects (`/api/v1/projects`):**
  - `GET /` — List available projects
  - `POST /` — Create a new project (`{"name": str, "project_id": str}`)
  - `GET /{project_id}` — Get project metadata
  - `PUT /{project_id}` — Update project metadata
  - `DELETE /{project_id}` — Delete project
- **ETL (`/api/v1/projects/{project_id}/etl`):**
  - `GET /dag` — Fetch saved pipeline DAG
  - `PUT /dag` — Save pipeline DAG (`{"nodes": [], "edges": []}`)
  - `POST /execute` — Execute ETL pipeline
  - `GET /jobs/{job_id}` — Poll background job status
- **Dashboards (`/api/v1/projects/{project_id}/dashboards`):**
  - `GET /` — List project dashboards
  - `POST /` — Create new dashboard
  - `GET /{dashboard_id}` — Get dashboard layout & bindings
  - `PUT /{dashboard_id}` — Save dashboard layout & bindings
  - `DELETE /{dashboard_id}` — Delete dashboard
- **Files (`/api/v1/projects/{project_id}/files`):**
  - `GET /` — List uploaded data files
  - `POST /` — Upload CSV, Parquet, or SQLite file
  - `DELETE /{filename}` — Delete specific data file
- **Viewer (`/api/v1/viewer`):**
  - `GET /{project_id}/dashboards/{dashboard_id}/data` — Read-only aggregated widget data for rendering

---

## 🐳 Docker Deployment

The simplest way to run PyBI is using Docker and Docker Compose.

### Linux / macOS
```bash
chmod +x start.sh stop.sh
./start.sh
```
Access PyBI in your browser at: [http://localhost:8080](http://localhost:8080)

### Windows
```cmd
start.bat
```

---

## 🚀 Quickstart & Setup (Local Python)

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Launching the Application
```bash
python3 -m pybi.main
```

---

## 📄 Publishing & Export Engine

PyBI includes a robust Publishing & Export Engine (`pybi.export`) for freezing and sharing dynamic reports:
- **Multi-Format Output:** Generate static PDF, HTML, Markdown, or raw CSV data extracts.
- **Jinja2 Templating:** Customize output layouts using templates like `report_dati.html` and `documento_knowledge.md`.
- **Snapshot Immutability:** Every export generates a `snapshot.json` metadata file containing a unique `export_id`, timestamp, project version, and a SHA-256 hash of active filter rules (`active_filters_hash`).

---

## 🧪 Testing & Verification

Run tests locally using pytest:
```bash
python3 -m pytest
```
