# 🗺️ PYBI (Python Business Intelligence) - ROADMAP

Questo documento definisce le fasi di sviluppo del progetto PYBI, una piattaforma BI open-source 100% Python, pensata come alternativa moderna e leggera a PowerBI Desktop.

## 📌 Stato Attuale
- **Fasi Completate:** Fase 1 (Foundation & Scaffolding), Fase 2 (Core Data Engine & Visual Binding), Fase 2.5 (Advanced Analytics & Excel-like UX), Fase 3 (Persistence, Auth & Advanced Features), Fase 4 (Production Readiness & Polish), Fase 5 (Publishing & Export Engine) e Fase 6 (Decoupled REST API Architecture, Semantic Layer & RLS Foundations)
- **Stato Progetto:** Release 1.0 General Availability (✅ Produzione Pronta con Architettura API REST Decoupled)

---

## 🏆 Fase 6: Enterprise Parity & Production Hardening

- [ ] **Epic 1: Semantic Layer & Data Modeling**
  - [x] Task 1.1: Schema `pybi/core/semantic_model.py` per tabelle, colonne, relazioni (join keys) e misure calcolate.
  - [x] Task 1.2: Query resolution con JOIN automatici tra relazioni in DuckDB (`SemanticQueryResolver` e `pybi/core/query_resolver.py`).
  - [ ] Task 1.3: Binding UI Dashboard Editor per selezione "Misure" e "Dimensioni" semantiche.

- [ ] **Epic 2: Enterprise Connectors & DirectQuery**
  - [ ] Task 2.1: Refactoring connettori con `BaseConnector` (`read`, `write`, `test_connection`).
  - [ ] Task 2.2: Connettori Snowflake e Google BigQuery con SQLAlchemy/DuckDB Secret.
  - [ ] Task 2.3: Modalità DirectQuery in DuckDB per query live su sorgenti esterne.

- [ ] **Epic 3: Dynamic Row-Level Security (RLS)**
  - [x] Task 3.1: Estrazione claims JWT (`user_id`, `role`, `allowed_regions`).
  - [x] Task 3.2: `pybi/core/rls_engine.py` per iniezione clausole WHERE da regole RLS semantiche (`apply_rls_filters`).
  - [ ] Task 3.3: Test E2E per isolamento RLS.

- [ ] **Epic 4: ALM & Project Portability**
  - [ ] Task 4.1: `pybi/alm/bundler.py` per esportazione/importazione bundle `.pybi` (ZIP).
  - [ ] Task 4.2: Endpoint API `POST /api/v1/projects/import` per bundle `.pybi`.
  - [ ] Task 4.3: GitHub Actions CI workflow per pytest e ruff.

- [ ] **Epic 5: Osservabilità e Audit**
  - [ ] Task 5.1: Middleware FastAPI per audit logging accesses/queries.
  - [ ] Task 5.2: Endpoint `GET /api/v1/admin/usage-metrics`.

- [x] **Epic 6: Refactoring UI ETL Power Query Style (Applied Steps)**
  - [x] Task 6.1: Modelli Pydantic `ETLStep` ed `ETLQuery` per rappresentazione lineare della pipeline.
  - [x] Task 6.2: Esecuzione sequenziale `execute_linear_etl` e anteprima intermedia per `step_index` in `pybi/etl/executor.py`.
  - [x] Task 6.3: Nuova UI ETL Editor a 3 pannelli (Header, Data Grid interattiva con menu contestuali di colonna, Pannello Passaggi Applicati).
  - [x] Task 6.4: Endpoint API v1 `/api/v1/projects/{id}/etl/query`, `/execute` e `/preview` aggiornati.

---

## 🌐 Fase 5: Publishing & Export Engine (✅ COMPLETATA)
- [x] **Export Engine (`pybi.export`):** Generazione report PDF, HTML, Markdown e CSV.
- [x] **Snapshot Metadata:** File `snapshot.json` con hash SHA-256 dei filtri attivi.
- [x] **Jinja2 Templating:** Layout personalizzabili e worker queue asincrona.

---

## 🌐 Fase 6 (Precedente): Decoupled REST API Architecture (✅ COMPLETATA)
- [x] **Pydantic Schemas (`pybi/api/schemas.py`):** Modelli Pydantic per risorse API.
- [x] **API Routers `/api/v1/`:** Endpoints RESTful completi.
- [x] **Frontend Decoupling:** Client NiceGUI/Vue 3 consumano API REST v1.
