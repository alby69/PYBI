# 🧬 Semantic Model & Dynamic Row-Level Security (RLS)

## 1. Overview
The **PyBI Semantic Model** provides an enterprise abstraction layer between raw data sources (DuckDB tables, Parquet, CSVs) and analytical visual reporting widgets.

Key features include:
- **Multi-Table Relational Schema:** Defines relationships between tables (`1:1`, `1:*`, `*:1`, `*:*`).
- **Dimensions & Measures:** Explicit dimension attributes and calculated measure expressions (SQL/DuckDB aggregations).
- **YAML Specification (`semantic_model.yaml`):** Declarative version-controlled model definition.
- **Dynamic Row-Level Security (RLS):** Applies dynamic user filter context based on JWT auth claims before executing queries in DuckDB.

---

## 2. Declarative Specification (`semantic_model.yaml`)

```yaml
name: sales_enterprise_model
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
      - name: store_id
        column_name: store_id
        data_type: integer
    measures:
      - name: total_revenue
        expression: "SUM(amount)"
        label: "Total Revenue"
      - name: avg_order_value
        expression: "AVG(amount)"
        label: "Average Order Value"

  - name: stores
    source_table: store_dim
    columns:
      - name: store_id
        column_name: store_id
        data_type: integer
        is_key: true
      - name: country
        column_name: country
        data_type: string

relationships:
  - from_table: sales
    from_column: store_id
    to_table: stores
    to_column: store_id
    cardinality: "*:1"
    join_type: LEFT

rls_rules:
  - name: regional_isolation
    target_table: sales
    filter_expression: "region = '{user_allowed_region}'"
```

---

## 3. Gestione delle Relazioni tramite UI (Vista Modello Stile Power BI)

La **Model View** di PyBI fornisce un'esperienza utente pari a quella di Power BI per l'ispezione grafica e la modifica delle relazioni fra le tabelle semantiche.

### Flusso di lavoro passo-passo per l'utente:
1. **Aprire la Vista Modello:** Selezionare `/model-editor` dal menu di navigazione superiore.
2. **Creare una relazione tramite drag-and-drop:**
   - Nel canvas principale Vue Flow, trascinare una linea di connessione (edge) muovendosi dal **punto di aggancio (handle)** di un campo/colonna specifico in una scheda tabella al campo di destinazione in un'altra tabella.
3. **Modificare le proprietà reattive:**
   - Cliccare su qualsiasi linea di relazione per caricarla nel **Pannello delle Proprietà a destra**.
   - Selezionare o modificare la *Tabella di Origine/Destinazione* (i dropdown del *Campo di Origine/Destinazione* si popolano reattivamente con le relative colonne).
   - Ajustare la *Cardinalità* (`1:1`, `1:*`, `*:1`, `*:*`), il *Tipo di Join* (`LEFT`, `INNER`, `RIGHT`, `FULL`) o disattivare la relazione (toggle *Active*). Le relazioni attive appaiono come linee continue, quelle inattive come linee tratteggiate.
4. **Rilevamento Automatico (Autodetect):**
   - Cliccare sul pulsante **"Gestisci relazioni"** nella barra degli strumenti per aprire la finestra di dialogo modale.
   - Cliccare su **"Rileva automaticamente"** (Autodetect) per scansionare automaticamente i campi delle tabelle del modello e proporre relazioni tra colonne con nome e tipo di dato identici.

---

## 4. Automatic Multi-Table JOIN Resolution

When a semantic query requests dimensions or measures across multiple tables (e.g. `stores.country` dimension with `sales.total_revenue` measure), `SemanticQueryResolver` automatically:
1. Identifies the primary table (`sales`).
2. Traces relationship paths defined in `semantic_model.yaml`.
3. Constructs and executes optimized SQL in DuckDB:
   ```sql
   SELECT "stores"."country" AS "country", SUM("sales"."amount") AS "total_revenue"
   FROM "sales" AS "sales"
   LEFT JOIN "store_dim" AS "stores" ON "sales"."store_id" = "stores"."store_id"
   GROUP BY "stores"."country"
   ```
