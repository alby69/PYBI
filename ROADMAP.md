# 🗺️ PYBI (Python Business Intelligence) - ROADMAP

Questo documento definisce le fasi di sviluppo del progetto PYBI, una piattaforma BI open-source 100% Python, pensata come alternativa moderna e leggera a PowerBI Desktop.

## 📌 Stato Attuale
- **Fase Completata:** Fase 1 (Foundation & Scaffolding)
- **Prossima Fase:** Fase 2 (Core Data Engine & Visual Binding)

---

## 🏁 Fase 1: Foundation & Scaffolding (✅ COMPLETATA)
**Obiettivo:** Creare l'architettura di base, l'interfaccia utente e il ponte Vue-Python.
- [x] Setup del progetto con `pyproject.toml` e gestione dipendenze.
- [x] Integrazione frontend: NiceGUI (Vue 3 + Quasar).
- [x] Canvas ETL: Integrazione di Vue Flow (`@vue-flow/core`) come `ui.element` personalizzato.
- [x] Canvas Dashboard: Integrazione di Vue Grid Layout (`grid-layout-plus`) per widget drag-and-drop.
- [x] Routing di base: `/`, `/etl-editor`, `/dashboard-editor`, `/viewer`.
- [x] Ponte bidirezionale Vue-Python per la sincronizzazione reattiva di nodi, bordi e layout.

---

## 🚀 Fase 2: Core Data Engine & Visual Binding (🔄 IN CORSO)
**Obiettivo:** Rendere funzionale il motore di elaborazione dati e collegarlo all'interfaccia visuale.
- [ ] **ETL Execution Engine:** Tradurre il DAG JSON di Vue Flow in un piano di esecuzione Polars/DuckDB.
- [ ] **Data Connectors:** Implementare connettori di base (CSV, Parquet, SQLite) tramite Polars.
- [ ] **Dashboard Data Binding:** Collegare i widget della griglia a query DuckDB o DataFrame Polars in memoria.
- [ ] **Charting Integration:** Aggiungere un componente di grafici riutilizzabile (es. ECharts o Plotly) in NiceGUI.
- [ ] **Testing:** Scrivere test unitari ed E2E (Playwright) per il flusso ETL e il rendering dei grafici.

---

## 🔐 Fase 3: Persistence, Auth & Advanced Features
**Obiettivo:** Aggiungere persistenza dei progetti, sicurezza e funzionalità avanzate.
- [ ] **Auth & RBAC:** Implementare autenticazione completa con PyJWT e controllo degli accessi con Casbin.
- [ ] **Project Serialization:** Salvataggio e caricamento di pipeline ETL e layout dashboard su database (SQLite/PostgreSQL) o file system.
- [ ] **Advanced ETL Nodes:** Aggiungere nodi per Join, Merge, Pivot e aggregazioni complesse.
- [ ] **Scheduled Execution:** Supporto per l'esecuzione programmata di pipeline ETL (background tasks con FastAPI/Celery o asyncio).

---

## 🏆 Fase 4: Production Readiness & Polish
**Obiettivo:** Preparare il progetto per il rilascio pubblico e l'uso in produzione.
- [ ] **Dockerization:** Creare un `Dockerfile` e un `docker-compose.yml` per un deployment a colpo singolo.
- [ ] **Performance Optimization:** Ottimizzare le query DuckDB e la gestione della memoria per dataset di medie dimensioni (>1M righe).
- [ ] **Documentation:** Scrivere documentazione completa (README, guide per gli sviluppatori, tutorial per gli utenti finali).
- [ ] **CI/CD Pipeline:** Configurare GitHub Actions per linting, testing automatico e build dei container.

---

## 🤖 Linee Guida per l'Interazione con Google Jules
1. **Assegnazione Task:** Copiare il prompt specifico della fase (es. Fase 2) come nuova GitHub Issue o task diretto per Jules.
2. **Revisione:** Verificare che Jules crei commit atomici e separati per logica (es. un commit per i connettori, uno per l'executor).
3. **Validazione:** Eseguire sempre `python3 -m pytest tests/` e `python3 -m pybi.main` dopo ogni intervento di Jules per garantire la non-regressione.
4. **Gestione Context:** Se un task risulta troppo ampio per un singolo run di Jules, suddividerlo in sotto-task sequenziali (es. "Implementa solo i connettori CSV/Parquet" prima di "Implementa l'executor completo").