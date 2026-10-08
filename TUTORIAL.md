# PyBI — Tutorial Completo

Guida aggiornata alla piattaforma PyBI (Python Business Intelligence), inclusa la gestione multi-dashboard, autenticazione, motore di export e ottimizzazioni delle prestazioni.

---

## 1. Cos'è PyBI

PyBI è una piattaforma di business intelligence open-source, 100% Python, progettata come alternativa moderna e leggera a PowerBI Desktop.

Il flusso tipico è:
```
Progetto → ETL (DAG visuale) → Dashboard (Multi-layout) → Viewer / Export
```

---

## 2. Avvio Rapido

### Metodo Consigliato: Docker
```bash
# Linux / macOS
chmod +x start.sh stop.sh
./start.sh

# Windows
start.bat
```
Accedi a: http://localhost:8080

### Metodo Locale (Python 3.11+)
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 -m pybi.main --port 8080
```

---

## 3. Configurazione (.env)

Copia `.env.example` in `.env`. Le variabili chiave includono:
- `DATA_DIR`: Percorso di persistenza (default: `pybi_data`).
- `JWT_SECRET`: Chiave per l'autenticazione (Fase 3).
- `DUCKDB_THREADS` / `DUCKDB_MAX_MEMORY`: Ottimizzazione prestazioni per dataset grandi (Fase 4).

---

## 4. Gestione Progetti e Multi-Dashboard

Ogni progetto è isolato in `pybi_data/projects/<id>/` e contiene:
1. Un file `.json` di configurazione.
2. Una cartella `data/` per i file sorgente (CSV, Parquet, SQLite).
3. **Multi-Dashboard**: Un progetto può ospitare più layout di dashboard. Il `DashboardManager` permette di creare, rinominare, caricare ed eliminare dashboard specifiche (`dash_1`, `dash_2`, ecc.) con migrazione automatica dei progetti legacy.

Nell'ETL Editor, puoi **caricare, elencare ed eliminare** file direttamente nella cartella `data/` del progetto attivo, rendendoli immediatamente disponibili nel nodo "Data Source" senza percorsi assoluti.

---

## 5. ETL Editor (Fasi 1-3)

L'editor utilizza Vue Flow per un canvas interattivo.
- **Palette Nodi**: Data Source, Filter, Select Columns, Group By, Join Tables, Pivot, Output Table.
- **Pannello Proprietà**: Drawer laterale a scomparsa per modificare i parametri dei nodi.
- **Validazione**: Controllo preventivo di cicli e connessioni mancanti prima dell'esecuzione.
- **Scheduler (Fase 3)**: Le pipeline possono essere programmate per l'esecuzione in background tramite `pybi.etl.scheduler`.

### Esempio Join
Il nodo "Join Tables" richiede **esattamente due input**. Il primo collegamento è la tabella sinistra, il secondo la destra. Supporta: `inner`, `left`, `right`, `full`, `cross`, `semi`, `anti`.

---

## 6. Dashboard Editor & Pivot Table (Fase 2.5)

- **Griglia Drag-and-Drop**: Basata su `grid-layout-plus` per posizionare widget (KPI, Barre, Linee, Torta, Tabelle).
- **Pivot Table Avanzata**: Widget stile Excel con drag & drop di campi (righe, colonne, valori). Per dataset >50.000 righe, attiva automaticamente un **fallback di aggregazione lato server** tramite DuckDB per garantire prestazioni istantanee.
- **Binding Dati**: I widget si collegano alle tabelle di output dell'ETL registrate nel `default_binder`.

---

## 7. Motore di Publishing & Export (Fase 5)

Il sistema permette di "congelare" una dashboard in un artefatto statico e versionato.
- **Formati**: PDF, HTML, Markdown, CSV.
- **Templating**: Motore Jinja2 con template personalizzabili (`report_dati.html`, `documento_knowledge.md`).
- **Immutabilità**: Ogni export genera un `snapshot.json` con ID univoco, timestamp e hash SHA-256 dei filtri attivi (`active_filters_hash`).
- **AI-Assisted**: Supporta un `ai_compilation_prompt` nei metadati per guidare la sintesi del documento.
- **API**:
  - `POST /api/projects/{id}/export` (avvio job asincrono)
  - `GET /api/exports/{id}/status` (polling stato)
  - `GET /api/exports/{id}/download` (download artefatto)

---

## 8. Autenticazione e Sicurezza (Fase 3)

- **JWT + Casbin**: Gestione ruoli (RBAC) per controllare l'accesso a progetti, esecuzione ETL e funzioni di export.
- I token sono gestiti in modo trasparente dall'interfaccia e validati a ogni richiesta API.

---

## 9. Testing e CI/CD (Fase 4)

Il progetto include oltre 190 test (unitari, E2E con Playwright, performance).
```bash
# Esecuzione locale dei test
pip install pytest playwright
playwright install --with-deps chromium
python3 -m pytest tests/ -q
```
La pipeline GitHub Actions (`.github/workflows/ci.yml`) esegue automaticamente linting, test e build Docker ad ogni push.

---

## 10. Diagnostica e Limitazioni Note

- **Log**: Usa `docker compose logs -f` per debuggare errori ETL (es. dipendenze mancanti che causano HTTP 500).
- **Limitazione**: Il binding delle tabelle DuckDB è in memoria. Dopo un riavvio del server, è necessario rieseguire la pipeline ETL per popolare i widget della dashboard (a meno che non si usi `Output Type = sqlite`).
- **PostgreSQL**: Il connettore è implementato e testato, ma l'esposizione nella palette UI è in fase di finalizzazione.

---
*Per dettagli architetturali avanzati, consulta `docs/PHASE5_EXPORT_SPEC.md` e il codice sorgente in `pybi/export/`.*
