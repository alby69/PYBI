# 🗺️ PYBI (Python Business Intelligence) - ROADMAP

Questo documento definisce le fasi di sviluppo del progetto PYBI, una piattaforma BI open-source 100% Python, pensata come alternativa moderna e leggera a PowerBI Desktop.

## 📌 Stato Attuale
- **Fasi Completate:** Fase 1 (Foundation & Scaffolding), Fase 2 (Core Data Engine & Visual Binding), Fase 2.5 (Advanced Analytics & Excel-like UX), Fase 3 (Persistence, Auth & Advanced Features), Fase 4 (Production Readiness & Polish) e Fase 5 (Publishing & Export Engine)
- **Stato Progetto:** Release 1.0 General Availability (✅ Produzione Pronta con Engine di Export Completo)

---

## 🏁 Fase 1: Foundation & Scaffolding (✅ COMPLETATA)
**Obiettivo:** Creare l'architettura di base, l'interfaccia utente e il ponte Vue-Python.
- [x] Setup del progetto con `pyproject.toml` e gestione dipendenze.
- [x] Integrazione frontend: NiceGUI (Vue 3 + Quasar).
- [x] Canvas ETL: Integrazione di Vue Flow (`@vue-flow/core`) come `ui.element` personalizzato.
- [x] Canvas Dashboard: Integrazione di Vue Grid Layout (`grid-layout-plus`) per widget drag-and-drop.
- [x] Routing di base: `/`, `/etl-editor`, `/dashboard-editor`, `/viewer`.
- [x] Ponte bidirezionale Vue-Python per la sincronizzazione reattiva di nodi, bordi e layout.
- [x] **Dockerization:** Creare un `Dockerfile` e un `docker-compose.yml` per un deployment a colpo singolo.

---

## 🚀 Fase 2: Core Data Engine & Visual Binding (✅ COMPLETATA)
**Obiettivo:** Rendere funzionale il motore di elaborazione dati e collegarlo all'interfaccia visuale.
- [x] **ETL Execution Engine:** Tradurre il DAG JSON di Vue Flow in un piano di esecuzione Polars/DuckDB.
- [x] **Data Connectors:** Implementare connettori di base (CSV, Parquet, SQLite, PostgreSQL) tramite Polars.
- [x] **Dashboard Data Binding:** Collegare i widget della griglia a query DuckDB o DataFrame Polars in memoria.
- [x] **Charting Integration:** Aggiungere un componente di grafici riutilizzabile in NiceGUI.
- [x] **Testing:** Scrivere test unitari ed E2E (Playwright) per il flusso ETL e il rendering dei grafici.

---

## 📊 Fase 2.5: Advanced Analytics & Excel-like UX (✅ COMPLETATA)
**Obiettivo:** Arricchire la piattaforma con strumenti avanzati di analisi ed esperienze interattive stile foglio di calcolo.
- [x] **Pivot Table Widget:** Implementazione del widget Pivot Table interattivo con drag & drop di campi (righe, colonne, valori).
- [x] **Multiple Aggregations:** Supporto a funzioni di aggregazione dinamiche (Somma, Conteggio, Media, Min, Max).
- [x] **CSV Export:** Esportazione dei dati pivotati in formato CSV.
- [x] **Server-side Fallback:** Aggregazione dinamica lato server con DuckDB per dataset di grandi dimensioni (>50k righe).

---

## 🔐 Fase 3: Persistence, Auth & Advanced Features (✅ COMPLETATA)
**Obiettivo:** Aggiungere persistenza dei progetti, sicurezza e funzionalità avanzate.
- [x] **Auth & RBAC:** Implementare autenticazione completa con PyJWT e controllo degli accessi con Casbin.
- [x] **Project Serialization:** Salvataggio e caricamento di pipeline ETL e layout dashboard su database (SQLite/PostgreSQL) o file system.
- [x] **Advanced ETL Nodes:** Aggiungere nodi per Join, Merge, Pivot e aggregazioni complesse.
- [x] **Scheduled Execution:** Supporto per l'esecuzione programmata di pipeline ETL (background tasks con FastAPI/Celery o asyncio).

---

## 🏆 Fase 4: Production Readiness & Polish (✅ COMPLETATA)
**Obiettivo:** Preparare il progetto per il rilascio pubblico e l'uso in produzione.
- [x] **Performance Optimization:** Ottimizzazione configurabile delle query DuckDB e gestione della memoria/thread (`threads`, `max_memory` pragmas, zero-copy evaluation) per dataset di medie e grandi dimensioni (>1M righe).
- [x] **Documentation:** Documentazione completa ed aggiornata (README, TUTORIAL, guida sviluppatori, architettura, deployment).
- [x] **CI/CD Pipeline:** Configurazione GitHub Actions (`.github/workflows/ci.yml`) per testing automatico (pytest + async), linting e build del container Docker.

---

## 📄 Fase 5: Publishing & Export Engine (✅ COMPLETATA)
**Obiettivo:** Fornire un motore di esportazione e pubblicazione asincrono che trasforma dashboard e conoscenza dinamica in artefatti statici e versionati (PDF, HTML, Markdown, CSV).
- [x] **Export Multi-Formato:** Generazione di PDF, HTML, Markdown e CSV per archiviazione e condivisione.
- [x] **Templating Engine (Jinja2):** Supporto a template personalizzabili (`report_dati.html`, `documento_knowledge.md`).
- [x] **Snapshot Versioning & Immutabilità:** Generazione di metadata `snapshot.json` con ID univoco e hash SHA-256 dei filtri attivi (`active_filters_hash`).
- [x] **FilterContext Binding (`bind_filter_context`):** Applicazione automatica dei filtri attivi e valutazione del modello semantico prima della generazione degli export.
- [x] **Generazione Assistita da AI:** Integrazione del prompt di compilazione assistita (`ai_compilation_prompt`) serializzato nei metadata di snapshot.
- [x] **API REST Asincrona:** Endpoint per avvio job, polling dello stato (`/api/exports/{id}/status`) e download dell'artefatto (`/api/exports/{id}/download`).
- [x] **Interfaccia Utente:** Modal dialog "Publish & Export" integrato nell'interfaccia con scelta formato, template, prompt AI ed indicatore di progresso in tempo reale.

---

## 🤖 Linee Guida per l'Interazione con Google Jules
1. **Assegnazione Task:** Copiare il prompt specifico della fase come nuova GitHub Issue o task diretto per Jules.
2. **Revisione:** Verificare che Jules crei commit atomici e separati per logica.
3. **Validazione:** Eseguire sempre `python3 -m pytest tests/` e `python3 -m pybi.main` dopo ogni intervento di Jules per garantire la non-regressione.
4. **Gestione Context:** Se un task risulta troppo ampio per un singolo run di Jules, suddividerlo in sotto-task sequenziali.
