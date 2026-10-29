# 🏛️ PyBI Architecture Overview

## 1. System Vision & Principles
PyBI (Python Business Intelligence) is an open-source, 100% Python-based enterprise BI platform designed with a decoupled API-first architecture, Power BI-style semantic layer, and native AI integration via the Model Context Protocol (MCP).

### Guiding Architectural Principles
- **KISS (Keep It Simple, Stupid):** Streamlined DuckDB and Polars execution without unnecessary operational overhead.
- **DRY (Don't Repeat Yourself):** Centralized semantic model definitions and single-source documentation.
- **API-First:** Pure REST API backend (`backend/api/v1`) with independent web frontend.
- **Separation of Concerns:** Distinct separation between business logic (`backend/core`), query engines (`backend/etl`, `backend/core/dax_engine`), and presentation.

---

## 2. Directory Layout & Module Responsibilities

```text
pybi-repo/
├── README.md                 # Minimal root README with quickstart and docs links
├── pyproject.toml            # Unified dependency definition
├── docker-compose.yml        # Multi-container orchestration
│
├── backend/                  # Pure Business Logic, Semantic Model & REST API
│   ├── main.py               # FastAPI application entry point
│   ├── api/v1/               # Versioned REST routers (semantic, etl, mcp, viewer)
│   ├── core/                 # Core domain layer (interfaces, DAX engine, RLS, resolver)
│   ├── etl/                  # Connectors, compilers, and query folding
│   └── mcp/                  # MCP Server and tools implementation
│
├── frontend/                 # Decoupled Web Frontend Client
│   ├── package.json
│   └── src/                  # Vue components, stores, composables, and API services
│
└── docs/                     # Consolidated Documentation
    ├── 01_architecture.md
    ├── 02_semantic_layer_dax.md
    ├── 03_mcp_ai_integration.md
    ├── 04_api_reference.md
    └── 05_developer_guide.md
```
