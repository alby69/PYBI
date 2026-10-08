# 🗺️ PYBI (Python Business Intelligence) - ROADMAP

Questo documento definisce le fasi di sviluppo del progetto PYBI, una piattaforma BI open-source 100% Python, pensata come alternativa moderna e leggera a PowerBI Desktop.

## 📌 Stato Attuale
- **Fasi Completate:** Fase 1 (Foundation & Scaffolding), Fase 2 (Core Data Engine & Visual Binding), Fase 2.5 (Advanced Analytics & Excel-like UX), Fase 3 (Persistence, Auth & Advanced Features), Fase 4 (Production Readiness & Polish), Fase 5 (Publishing & Export Engine) e Fase 6 (Decoupled REST API Architecture)
- **Stato Progetto:** Release 1.0 General Availability (✅ Produzione Pronta con Architettura API REST Decoupled)

---

## 🌐 Fase 6: Decoupled REST API Architecture (✅ COMPLETATA)
**Obiettivo:** Disaccoppiare nettamente il frontend dal backend trasformando il backend in un servizio FastAPI RESTful puro e aggiornando il frontend per consumare le API `/api/v1/`.
- [x] **Pydantic Schemas (`pybi/api/schemas.py`):** Modelli Pydantic per Projects, ETL DAG, Dashboards, Files, Jobs, e Viewer payloads.
- [x] **Storage Refactoring (`pybi/storage/project_manager.py`):** Metodi granulari per gestione progetti, DAG, layout e file.
- [x] **API Routers `/api/v1/`:** Endpoints RESTful completi per `/projects`, `/etl`, `/dashboards`, `/files` e `/viewer`.
- [x] **Frontend Decoupling:** Aggiornamento delle pagine NiceGUI (`etl_editor.py`, `dashboard_editor.py`, `viewer.py`) e dei componenti (`ProjectManager`).
- [x] **Standardized Error Handling:** Gestore eccezioni globale con risposta JSON standardizzata `{"detail": "...", "code": "API_ERROR"}`.

---

## 🏆 Fase 4: Production Readiness & Polish (✅ COMPLETATA)
- [x] **Performance Optimization:** Query DuckDB e pragmas di memoria.
- [x] **CI/CD Pipeline:** Test automatici pytest ed E2E.
