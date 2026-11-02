# 🏛️ PyBI Architecture Overview

## 1. System Vision & Principles
PyBI (Python Business Intelligence) is an open-source, 100% Python-based BI platform built as an integrated Python application with a REST API, a Power BI-style semantic layer, and AI integration via the Model Context Protocol (MCP).

### Guiding Architectural Principles
- **KISS (Keep It Simple, Stupid):** Streamlined DuckDB and Polars execution without unnecessary operational overhead.
- **DRY (Don't Repeat Yourself):** Centralized semantic model definitions and single-source documentation.
- **Canonical Package:** `pybi` is the canonical package for application behavior and runtime wiring.
- **Compatibility:** `backend` preserves historical import paths and delegates to implementations in `pybi`.
- **Separation of Concerns:** API, semantic, ETL, export, storage, and UI responsibilities are grouped under `pybi`; this is not yet a strict ports-and-adapters architecture.

---

## 2. Current Package Layout & Module Responsibilities

```text
pybi-repo/
├── README.md                 # Minimal root README with quickstart and docs links
├── pyproject.toml            # Unified dependency definition
├── docker-compose.yml        # Multi-container orchestration
│
├── pybi/                     # Canonical application package
│   ├── main.py               # NiceGUI application entry point
│   ├── api/                  # REST application wiring, schemas, and routes
│   ├── core/                 # Shared interfaces, storage, semantic and query helpers
│   ├── etl/                  # Connectors, compilers, execution, and scheduling
│   ├── mcp_integration/      # MCP server and tool implementations
│   ├── model/                # DAX translation helpers
│   ├── semantic/             # Semantic query behavior
│   ├── export/               # Export workflows
│   ├── publish/              # Publishing workflows
│   ├── frontend/             # Vue components and JavaScript frontend modules
│   └── ui/                   # NiceGUI pages, components, and static assets
│
├── backend/                  # Legacy import-compatible facades to pybi
│   ├── main.py               # Compatibility entry point for the REST app
│   ├── api/ core/ etl/       # Compatibility modules; implementations live in pybi
│   └── mcp/ models/ engine/  # Compatibility modules; implementations live in pybi
│
└── docs/                     # Consolidated Documentation
    ├── 01_architecture.md
    ├── 02_semantic_layer_dax.md
    ├── 03_mcp_ai_integration.md
    ├── 04_api_reference.md
    └── 05_developer_guide.md
```

`backend` is retained for existing imports and deployment commands. Its modules re-export or alias the corresponding `pybi` implementations; new code should import from `pybi`. The application is integrated: the Vue components live under `pybi/frontend`, while the primary UI runtime is NiceGUI. The `backend.main` command remains available as a compatibility entry point for the REST application.
