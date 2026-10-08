# PyBI — Tutorial Completo

Guida aggiornata alla piattaforma PyBI (Python Business Intelligence), inclusa l'architettura API REST disaccoppiata (`/api/v1/`), la gestione multi-dashboard, l'autenticazione ed il motore di export.

---

## 1. Cos'è PyBI

PyBI è una piattaforma di business intelligence open-source, 100% Python, progettata con un'architettura API-First disaccoppiata:
```
Frontend Client (NiceGUI)  <--- HTTP REST API /api/v1 --->  Backend FastAPI (DuckDB + Polars)
```

---

## 2. API REST v1 (/api/v1)

PyBI offre router FastAPI dedicati per la gestione completa delle risorse:

### Gestione Progetti
- `GET /api/v1/projects`: Elenco progetti.
- `POST /api/v1/projects`: Creazione progetto (`{"name": "...", "project_id": "..."}`).
- `GET /api/v1/projects/{id}`: Dettagli progetto.
- `PUT /api/v1/projects/{id}`: Aggiornamento metadati.
- `DELETE /api/v1/projects/{id}`: Eliminazione progetto.

### Gestione ETL Pipeline
- `GET /api/v1/projects/{id}/etl/dag`: Recupera il DAG salvato.
- `PUT /api/v1/projects/{id}/etl/dag`: Salva il DAG (`{"nodes": [], "edges": []}`).
- `POST /api/v1/projects/{id}/etl/execute`: Esegue la pipeline.
- `GET /api/v1/projects/{id}/etl/jobs/{job_id}`: Polling dello stato del job.

### Gestione Multi-Dashboard
- `GET /api/v1/projects/{id}/dashboards`: Lista dashboard.
- `POST /api/v1/projects/{id}/dashboards`: Crea nuova dashboard.
- `GET /api/v1/projects/{id}/dashboards/{dash_id}`: Layout e binding.
- `PUT /api/v1/projects/{id}/dashboards/{dash_id}`: Salva layout e binding.
- `DELETE /api/v1/projects/{id}/dashboards/{dash_id}`: Elimina dashboard.

### Gestione File Dati
- `GET /api/v1/projects/{id}/files`: Lista file data source.
- `POST /api/v1/projects/{id}/files`: Upload multipart (CSV, Parquet, SQLite).
- `DELETE /api/v1/projects/{id}/files/{filename}`: Elimina file.

---

## 3. Avvio Rapido

### Metodo Docker
```bash
chmod +x start.sh stop.sh
./start.sh
```
Accedi a: http://localhost:8080

### Metodo Locale
```bash
pip install -r requirements.txt
python3 -m pybi.main
```
