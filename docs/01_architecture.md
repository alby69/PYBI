# 🏗️ PyBI Architecture & Technical Specifications

## 1. High-Level System Architecture

PyBI is designed as a decoupled, API-First Business Intelligence platform.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Frontend Layer (NiceGUI / Vue 3)             │
│  ┌───────────────────────┐  ┌────────────────────┐  ┌───────────────┐ │
│  │ Vue Flow ETL Canvas   │  │ Dashboard Grid UI  │  │ Viewer Engine │ │
│  └───────────┬───────────┘  └─────────┬──────────┘  └───────┬───────┘ │
└──────────────┼────────────────────────┼─────────────────────┼─────────┘
               │                        │                     │
               ▼                        ▼                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI REST API Layer (/api/v1/)               │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────┐  ┌─────────────┐  │
│  │ ETL Router │  │ Dashboards   │  │ Semantic Query│  │ Export API  │  │
│  └─────┬──────┘  └──────┬───────┘  └───────┬───────┘  └──────┬──────┘  │
└────────┼────────────────┼──────────────────┼─────────────────┼─────────┘
         │                │                  │                 │
         ▼                ▼                  ▼                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      Core Analytical & Storage Engine                  │
│  ┌───────────────────────┐  ┌───────────────────────────────────────┐ │
│  │ Polars Engine (ETL)   │  │ DuckDB Engine (SQL & Query Folding)   │ │
│  └───────────────────────┘  └───────────────────────────────────────┘ │
│  ┌───────────────────────┐  ┌───────────────────────────────────────┐ │
│  │ Semantic Model Engine │  │ Redis Cache & File Project Storage    │ │
│  └───────────────────────┘  └───────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

## 2. Technology Stack

- **Backend:** Python 3.12, FastAPI, Pydantic v2, PyJWT, Casbin (RBAC)
- **Analytical Engine:** DuckDB (In-process OLAP, SQLGlot query transpilation), Polars (In-memory DataFrames & ETL transformations)
- **Caching & Connectors:** Redis (Query result caching), SQLAlchemy (Multi-database connectivity: Snowflake, BigQuery, PostgreSQL, SQLite)
- **Frontend Core:** NiceGUI, Vue 3, Quasar Framework, Pinia UI Store, Vega-Lite (Declarative visualizations)
- **Canvas Components:** `@vue-flow/core` (ETL DAG Editor), `grid-layout-plus` (Dashboard Grid Editor)
- **Export & Publishing:** Jinja2, WeasyPrint (PDF compilation), Async Background Task Worker Queue
