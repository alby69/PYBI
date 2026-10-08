# 🔍 OpenBI / PyBI - Python Business Intelligence Platform

**PyBI** (Python Business Intelligence) is an open-source, 100% Python-based BI platform designed as a modern alternative to PowerBI Desktop.

---

## 🏗️ Architecture & Stack (Declarative Schema-Driven UI)

- **Frontend Core:** Vue 3 & Quasar with **Declarative JSON-to-UI Engine (`DynamicRenderer`)**
- **UI State Management:** Pinia / Vue Reactive Store (`uiStore.js`) fetching schemas from FastAPI (`/api/ui/schema/{page_name}`)
- **ETL Visual Canvas:** [Vue Flow (`@vue-flow/core`)](https://vueflow.dev/) wrapped as a custom UI element
- **Dashboard Grid Canvas:** [Vue Grid Layout (`grid-layout-plus`)](https://grid-layout-plus.netlify.app/) wrapped as a custom UI element
- **Analytical Engine:** DuckDB + Polars
- **Publishing & Export Engine:** Headless Jinja2 + WeasyPrint / Async Worker Queue
- **API & Server:** FastAPI + Uvicorn
- **Auth & RBAC:** Casbin + PyJWT

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

## 🌐 Routes, Features & Declarative UI API

- **`/` (Home):** Project portal navigation.
- **`/etl-editor` (ETL DAG Editor):**
  - Interactive pipeline canvas powered by Vue Flow.
  - Node palette, property editor, validation & background execution scheduler.
- **`/dashboard-editor` (Dashboard Editor):**
  - Drag-and-drop & resizable widget grid powered by Vue Grid Layout.
  - Multi-format asynchronous publishing & export (PDF, HTML, Markdown, CSV).
- **`/viewer` (Public Read-Only Viewer):**
  - Schema-driven read-only dashboard view (`DynamicRenderer`) for end-user consultation.

### 📐 Declarative UI Schema Endpoints
- **`GET /api/ui/schema/{page_name}`**: Returns structured JSON UI schema describing page controls, Quasar layouts, and data bindings (`viewer`, `etl-editor`, etc.).
```json
{
  "page": "viewer",
  "components": [
    {
      "type": "q-toolbar",
      "props": { "class": "bg-primary text-white" },
      "children": [
        { "type": "q-toolbar-title", "text": "Executive Sales Dashboard" }
      ]
    },
    {
      "type": "custom:dashboard-grid",
      "props": { "isDraggable": false, "isResizable": false },
      "dataBinding": "state:viewer.layout"
    }
  ]
}
```

---

## 📄 Publishing & Export Engine

PyBI includes a robust Publishing & Export Engine (`pybi.export_engine`) for freezing and sharing dynamic reports:
- **Multi-Format Output:** Generate static PDF, HTML, Markdown, or raw CSV data extracts.
- **Jinja2 Templating:** Customize output layouts using templates like `report_dati.html` and `documento_knowledge.md`.
- **Snapshot Immutability:** Every export generates a `snapshot.json` metadata file containing a unique `export_id`, timestamp, project version, and a SHA-256 hash of active filter rules (`active_filters_hash`).
- **REST API Endpoints:**
  - `POST /api/projects/{id}/export`: Initiate background export task.
  - `POST /api/projects/{id}/export/pdf`: PDF shortcut endpoint.
  - `POST /api/projects/{id}/export/data`: CSV shortcut endpoint.
  - `GET /api/exports/{export_id}/status`: Poll background task status and snapshot metadata.
  - `GET /api/exports/{export_id}/download`: Download generated artifact file.

---

## 🧪 Testing & Verification

Run tests locally using pytest:
```bash
python3 -m pytest tests/ -q
```
