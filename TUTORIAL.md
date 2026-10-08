# PyBI — Tutorial Completo

Guida aggiornata alla piattaforma PyBI (Python Business Intelligence), inclusa l'architettura API REST disaccoppiata (`/api/v1/`), la gestione del modello semantico, le regole RLS, l'autenticazione ed il motore di export.

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

## 3. Avvio Rapido & Configurazione

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

---

### 3.5 Configurazione del Modello Semantico e RLS

Il Modello Semantico permette di definire relazioni tra tabelle, dimensioni, misure e regole di Row-Level Security (RLS) in un file YAML versionato (`semantic_model.yaml`).

#### Esempio Pratico: `semantic_model.yaml`

```yaml
name: enterprise_sales_model
tables:
  - name: sales
    source_table: sales_data
    columns:
      - name: sale_id
        column_name: sale_id
        data_type: integer
        is_key: true
      - name: region
        column_name: region
        data_type: string
      - name: amount
        column_name: amount
        data_type: float
    measures:
      - name: total_sales
        expression: "SUM(amount)"
        agg_func: "SUM"
        label: "Total Sales Amount"
      - name: avg_sale
        expression: "AVG(amount)"
        agg_func: "AVG"
        label: "Average Sale Amount"

  - name: customers
    source_table: customer_dim
    columns:
      - name: customer_id
        column_name: customer_id
        data_type: integer
        is_key: true
      - name: customer_name
        column_name: customer_name
        data_type: string

relationships:
  - from_table: sales
    from_column: customer_id
    to_table: customers
    to_column: customer_id
    cardinality: "*:1"
    join_type: LEFT

rls_rules:
  - name: restrict_user_region
    target_table: sales
    filter_expression: "region = '{user_allowed_region}'"
```

In Docker, le opzioni di connessione enterprise (es. Redis caching, credenziali Snowflake/BigQuery) possono essere configurate tramite le variabili d'ambiente nel file `.env`:
```env
REDIS_HOST=localhost
REDIS_PORT=6379
SNOWFLAKE_ACCOUNT=xy12345.eu-central-1
BIGQUERY_PROJECT_ID=my-gcp-project
```
