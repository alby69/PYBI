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

## 🌐 Routes & Phase 0 Features

- **`/` (Home):** Welcome dashboard & portal navigation.
- **`/etl-editor` (ETL DAG Editor):**
  - Interactive pipeline canvas powered by Vue Flow.
  - Reactive `nodes` and `edges` state synced bidirectionally between Python and Vue frontend.
  - Event listeners for node repositioning (`node_drag_stop`), connection creation (`connect`), and pipeline modifications (`change`).
- **`/dashboard-editor` (Dashboard Editor):**
  - Drag-and-drop & resizable widget grid powered by Vue Grid Layout.
  - Supports KPI cards, bar charts, data tables, and custom cards.
  - Real-time layout updates emitted to Python backend.
- **`/viewer` (Public Read-Only Viewer):**
  - Read-only dashboard view (`is_draggable=False`, `is_resizable=False`) for end-user consultation.

---

## 🧪 Testing & Verification

Run the automated test suite with Playwright:
```bash
python3 tests/test_e2e.py
```

---

## 🌁 Vue-Python Bridge Architecture

NiceGUI's `ui.element` is extended with custom JS files (`flow_editor.js` and `dashboard_grid.js`).
Since NiceGUI provides an ES importmap mapping `"vue"` to NiceGUI's internal Vue 3 instance, importing libraries (`@vue-flow/core` and `grid-layout-plus`) directly via browser ESM preserves a single, unified Vue context with zero duplicate library overhead.
Events emitted from Vue (`$emit`) automatically trigger registered Python callback handlers in real time.
