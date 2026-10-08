# PyBI — Tutorial

Guida completa al progetto: come avviarlo, come si usa l'editor ETL, come si
leggono i dati nel dashboard e quali comandi eseguire.

---

## 1. Cos'è PyBI

PyBI è una piattaforma di business intelligence in locale, composta da tre
pagine web collegate:

| Pagina | URL | A cosa serve |
|---|---|---|
| **Project Manager** | `/` | Crea, seleziona, rinomina ed elimina i progetti |
| **ETL Editor** | `/etl-editor` | Costruisce il flusso di trasformazione dati (canvas visuale) |
| **Dashboard Editor** | `/dashboard-editor` | Posiziona grafici e tabelle su una griglia e li collega ai dati |
| **Viewer** | `/viewer` | Dashboard in sola lettura, a schermo intero |

Il flusso tipico è:

```
Progetto  →  ETL (CSV → trasformazioni → tabella)  →  Dashboard  →  Viewer
```

Tutto gira in locale: nessun dato esce dalla macchina.

---

## 2. Avvio rapido con Docker (metodo consigliato)

```bash
./start.sh
```

Lo script esegue `docker compose up -d --build`, quindi ricostruisce l'immagine e
avvia il container. Al termine apri <http://localhost:8080>.

Per fermare tutto:

```bash
./stop.sh
```

Su Windows esistono gli equivalenti `start.bat` e `stop.bat`.

### Comandi Docker manuali

```bash
docker compose up -d --build   # build + avvio in background
docker compose up -d           # avvio senza rebuild
docker compose logs -f         # log in tempo reale (per vedere errori ETL)
docker compose ps              # stato dei container
docker compose down            # ferma e rimuove i container
docker compose restart         # riavvia senza rebuild
```

### Avvio senza Docker

Serve Python 3.11+ e un ambiente virtuale:

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 -m pybi.main
```

Oppure, se il pacchetto è installato in editable mode:

```bash
pip install -e .
pybi --port 8080
```

### Opzioni della CLI

| Flag | Default | Descrizione |
|---|---|---|
| `--port` | `8080` | Porta su cui il server ascolta |
| `--host` | `0.0.0.0` | Interfaccia di rete (usare `127.0.0.1` per limitare l'accesso) |

Esempio: `pybi --port 9090 --host 127.0.0.1`

---

## 3. Configurazione

La configurazione passa da un file `.env` (creato da `.env.example`):

```bash
cp .env.example .env
```

| Variabile | Default | Descrizione |
|---|---|---|
| `DATA_DIR` | `pybi_data` | Dove vengono salvati progetti e database locali |
| `PORT` | `8080` | Porta (usata da Docker) |
| `JWT_SECRET` | — | Chiave di firma dei token (per le funzioni di auth) |
| `DUCKDB_THREADS` | auto | Numero di thread allocati a DuckDB per l'elaborazione ETL |
| `DUCKDB_MAX_MEMORY` | auto | Limite massimo di RAM per DuckDB (es. `4GB`) |

**Attenzione:** il file `.env` contiene segreti ed è già in `.gitignore`. Non va
mai committato.

In Docker `DATA_DIR=/app/data` e la cartella `./pybi_data` della macchina viene
montata dentro il container, quindi i dati sopravvivono ai rebuild.

Risoluzione di `DATA_DIR` (`pybi/core/storage.py`):
`.env` → variabile d'ambiente `PYBI_DATA_DIR` → `<cwd>/pybi_data`.

---

## 4. Mappa del progetto

```
pybi/
├── main.py                     Server NiceGUI e rotte
├── core/storage.py             Percorsi dei dati, salvataggio/ caricamento progetti
├── storage/project_manager.py  Backend alternative su SQLite (non ancora usato)
├── etl/
│   ├── node_factory.py         Palette, parametri e validazione dei nodi
│   ├── executor.py             Motore di esecuzione del DAG (DuckDB + Polars)
│   └── connectors/             csv.py, parquet.py, sqlite.py, postgres.py
├── dashboard/binding.py        Collegamento tra tabelle e widget
├── datamodel/                  (stub, da implementare)
├── auth/                       (stub, da implementare)
├── ui/
│   ├── pages/                  etl_editor.py, dashboard_editor.py, viewer.py
│   ├── components/             flow_editor, dashboard_grid, project_manager, chart_widget
│   └── table_utils.py          Limite di righe per le anteprime
```

I `__init__.py` di `pybi/etl/connectors/` importano **tutti** i connettori in
blocco: se una dipendenza manca, l'intero pacchetto ETL smette di importare e
`/etl-editor` risponde con errore 500. I test in `tests/test_dependencies.py`
esistono proprio per intercettare questo prima del deploy.

---

## 5. I progetti

Ogni progetto ha una cartella dedicata con una sottocartella `data/` per i file dati (`pybi_data/projects/<id>/data/`) e un file JSON di configurazione in `pybi_data/projects/<id>.json` contenente:

```json
{
  "project_id": "default",
  "name": "default",
  "etl_dag": { "nodes": [...], "edges": [...] },
  "dashboard_layout": [],
  "created_at": "...",
  "updated_at": "..."
}
```

- `etl_dag` → il grafo ETL (nodi e archi)
- `dashboard_layout` → posizione dei widget del dashboard
- `name` → nome visualizzato

> `pybi_data/` è in `.gitignore`: i tuoi progetti restano in locale e non
> vengono pubblicati su GitHub.

Il **project manager** (home, `/`) permette di:

- **Create New Project** — crea il progetto attivo e lo apre nell'ETL editor
- **Switch** — cambia progetto attivo (ricarica editor e dashboard)
- **Rename** — rinomina; **il DAG e il layout vengono conservati**
- **Delete** — elimina definitivamente il progetto e la relativa cartella `data/`
- **Gestione File Dati Progetto** — permette di caricare file locali (CSV, Parquet, JSON, SQLite) nella cartella `data/` del progetto attivo, elencare i file caricati ed eliminarli direttamente dall'ETL Editor
- **Open** — riapre l'ultimo progetto attivo all'avvio del server

> Nota: eliminare un progetto non è reversibile. Non esiste un "cestino".

---

## 6. ETL Editor

### 6.1 Come si usa

1. Apri `/etl-editor`
2. Trascina un nodo dalla **palette** di sinistra sul canvas
3. Seleziona il nodo e compila i parametri nel pannello **Node Parameters**
   (sulla destra)
4. Collega le tabelle con un doppio click sul nodo di uscita (pallino in basso)
   fino al nodo di ingresso (pallino in alto) del nodo successivo
5. Premi **Execute Pipeline**

Il pulsante **Validate Graph** controlla la struttura del grafo senza eseguirlo.

L'editor funziona in due modi: *edit* (i parametri sono modificabili) e *view*
(il grafo diventa di sola lettura).

### 6.2 I sei tipi di nodo

#### Data Source — legge i dati

| Parametro | Obbligatorio | Note |
|---|---|---|
| `Source Type` | sì | `csv`, `parquet`, `sqlite` |
| `File Path` | sì | Percorso del file. I percorsi **relativi** sono risolti rispetto alla working directory del server, cioè `/app` dentro Docker (la root del progetto) |
| `Table / Query` | no | Per `sqlite`: nome della tabella **oppure una query SQL completa** (con `SELECT`) |

Esempi di percorso:
- `sales_data.csv` → il dataset di esempio, nella root del progetto
- `/app/output.db` → percorso assoluto
- `output.db` / `sales.db` → database SQLite

Il dataset di esempio `sales_data.csv` contiene 6 vendite:

```
id,region,product,sales,quantity
1,EU,Laptop,1200,3
2,US,Tablet,450,5
3,EU,Monitor,300,2
4,APAC,Phone,800,4
5,EU,Keyboard,100,10
6,US,Mouse,50,8
```

#### Filter — filtra le righe

| Parametro | Obbligatorio | Note |
|---|---|---|
| `Condition (WHERE)` | sì | Espressione SQL **senza la parola `WHERE`** |

La condizione viene valutata da DuckDB, quindi accetta `AND`, `OR`, `>`, `<`,
`IN`, `LIKE`, `BETWEEN`.

Esempi:

```
region = 'EU'
year >= 2024 AND region = 'EU'
category IN ('Laptop', 'Tablet')
city LIKE 'San%'
sales > 1000 AND year = 2023
```

> Attenzione alle stringhe: usano **apostrofi singoli**, non doppi.

#### Select Columns — sceglie e rinomina le colonne

| Parametro | Obbligatorio | Note |
|---|---|---|
| `Columns` | sì | Elenco separato da virgole. `*` per tutte. `nome AS nuovo_nome` per rinominare |

Esempi:

```
*
order_id, customer, region
order_id AS id, qty * price AS revenue
```

#### Group By — aggrega

| Parametro | Obbligatorio | Note |
|---|---|---|
| `Group By Columns` | sì | Elenco di colonne separato da virgole |
| `Aggregations` | no | Coppie `colonna:funzione`. Se vuoto, si conta il numero di righe |

Funzioni supportate:

```
sum   mean   min   max   count   first   last   median   std   n_unique
```

Esempi:

```
region:sum
year:sum,category:sum
```

Senza aggregazioni il risultato è `group_key` + `count`.

#### Output — salva il risultato

| Parametro | Obbligatorio | Note |
|---|---|---|
| `Table Name` | sì | Nome della tabella di output |
| `Output Type` | no | `duckdb` (default) oppure `sqlite` |
| `File Path` | per `sqlite` | Percorso del file `.db` |

Comportamento:
- **`duckdb`** → la tabella vive nella memoria del server ed è quella che il
  dashboard può mostrare. È la scelta standard.
- **`sqlite`** → scrive un file `.db` su disco, utile per conservare i dati o
  usarli come sorgente di un altro nodo.

### 6.3 Esempio funzionante (il dataset di esempio)

```
Data Source (csv, sales_data.csv)
      ↓
Filter  (region = 'EU')
      ↓
Output  (filtered_sales)
```

Risultato atteso: 3 righe su 6, con il log che mostra l'ordine di esecuzione e
le righe elaborate.

### 6.4 Collegare i nodi

- **Un nodo con un solo ingresso** è il caso normale.
- **Il nodo Join Tables accetta esattamente due ingressi**: il primo è la
  tabella sinistra, il secondo quella destra. Vedi la sezione 7.
- Su tutti gli altri nodi, più ingressi vengono ignorati: si usa il primo.

---

## 7. Join: come collegare due tabelle su un campo chiave

Il nodo **Join Tables** (icona 🔗) unisce due tabelle su una o più colonne chiave.
È l'unico nodo che legge due input.

### 7.1 Parametri

| Parametro | Obbligatorio | Note |
|---|---|---|
| `Left column` | sì (tranne `cross`) | Colonna chiave del **primo** ingresso |
| `Right column` | sì (tranne `cross`) | Colonna chiave del **secondo** ingresso. Le colonne sinistra e destra devono essere in numero uguale |
| `Join type` | sì | Tipo di join, vedi sotto |

Tipi di join disponibili:

| Tipo | Significato |
|---|---|
| `inner` | Tiene solo le righe che trovano corrispondenza in entrambe le tabelle |
| `left` | Tiene tutte le righe della tabella sinistra, completando con valori vuoti |
| `right` | Il contrario di `left` |
| `full` | Tiene tutte le righe di entrambe le tabelle |
| `cross` | Prodotto cartesiano: ogni riga sinistra con ogni riga destra. Non serve indicare le chiavi |
| `semi` | Tiene solo le colonne della tabella sinistra, filtrando sulle righe presenti a destra |
| `anti` | Tiene solo le righe sinistra che **non** hanno corrispondenza a destra |

### 7.2 Come si usa

1. Trascina **due** nodi Data Source (o qualsiasi altra catena di nodi)
2. Trascina il nodo **Join Tables**
3. Collega **prima** la tabella sinistra, **poi** quella destra: l'ordine delle
   connessioni conta
4. Compila `Left column`, `Right column` e `Join type`
5. Prosegui con `Select`, `Group By` o `Output`

L'ordine è importante: se inverti le connessioni, scambi sinistra e destra.

### 7.3 Esempio completo

L'esempio parte dai dati di esempio: `sales_data.csv` contiene le vendite, e ti
serve una seconda tabella con le informazioni delle regioni.

**Passo 0 — crea la tabella di lookup**

Crea `regions.csv` accanto a `sales_data.csv`:

```
region,region_manager,target
EU,Anna Rossi,1500
US,Marco Bianchi,1200
APAC,Li Wei,900
```

**Passo 1 — le due sorgenti**

```
Data Source (csv, sales_data.csv)                                         >  Join Tables  ->  Group By  ->  Output
Data Source (csv, regions.csv)      /
```

Nel nodo Join:

```
Left column : region
Right column: region
Join type   : inner
```

Poi `Group By` con `group_by = region_manager` e `aggregations = sales:sum`, e un
`Output` di nome `revenue_by_manager`.

Risultato atteso (verificato con i test):

```
region_manager | sales
Anna Rossi     | 1600     (Laptop 1200 + Monitor 300 + Keyboard 100)
Marco Bianchi  |  500     (Tablet 450 + Mouse 50)
Li Wei         |  800     (Phone 800)
```

Il log di esecuzione mostra la riga:

```
INNER joined on region: 4 rows
```

### 7.4 Come si comportano le colonne

- Se le due tabelle hanno colonne **non chiave** con lo stesso nome, polars
  aggiunge il suffisso `_right` alla seconda. Esempio: due colonne `sales`
  diventano `sales` e `sales_right`.
- La **colonna chiave destra viene unificata** in quella sinistra: se la chiave si
  chiama `region` a sinistra e `region_name` a destra, nel risultato trovi
  `region` e non più `region_name`.
- Per una **chiave composta**, indica più colonne separate da virgola nei due
  campi, nello stesso ordine:

  ```
  Left column : region, year
  Right column: region_name, year
  ```

- Se sbagli a scrivere il nome di una colonna, l'esecuzione si ferma con un
  errore che elenca le colonne disponibili, così sai subito cosa usare.

### 7.5 Errori tipici

| Errore | Causa |
|---|---|
| `requires two parent inputs` | Il nodo Join ha un solo ingresso: manca una delle due tabelle |
| `needs the same number of keys` | Hai indicato un numero diverso di chiavi a sinistra e a destra |
| `no column(s) ... Available columns: ...` | Nome della colonna chiave sbagliato |
| `Unsupported join type` | Tipo di join non valido (usa `outer` per `full`: viene tradotto) |

Il pulsante **Validate Graph** segnala questi problemi prima dell'esecuzione.
---

## 8. Dashboard Editor

1. Apri `/dashboard-editor`
2. Dal menu **Charts** scegli **Bar**, **Line** o **Pie**: viene inserito un
   widget nella griglia
3. **Aggiungi tabella** inserisce invece un widget tabella
4. Trascina i widget per posizionarli; le celle contengono una griglia di
   12 colonne per 8 righe
5. In un widget aperto in dettaglio trovi:
   - il **Data Source** (tabella da cui leggere)
   - la **colonna X** e la **colonna Y**
   - il **titolo**
6. **Refresh Data Source** ricarica i dati

I widget sono salvati nel `layout` del progetto insieme al DAG, quindi restano
associati al progetto e vengono ricaricati al ritorno sulla pagina.

> Nota: il collegamento tra tabelle e widget è attualmente **in memoria**
> (`pybi/dashboard/binding.py`) e vale per la sessione del server. Al prossimo
> riavvio le tabelle prodotte dall'ETL vanno rieseguite con **Execute Pipeline**
> per riempirsi.

---

## 9. Viewer

`/viewer` mostra la dashboard in sola lettura, a schermo intero, con lo stile
scuro: è la pagina da usare per proiettare o condividere il risultato. Non ha
controlli di modifica.

---

## 10. Comandi di riferimento

### Server

```bash
pybi --port 8080                    # avvia (pacchetto installato)
python3 -m pybi.main                # avvia senza installare
./start.sh                          # Docker: build + avvio
./stop.sh                           # Docker: arresto
```

### Progetti e dati

```bash
ls pybi_data/projects/              # elenco progetti salvati
cat pybi_data/projects/<id>.json    # ispeziona DAG e layout di un progetto
rm pybi_data/projects/<id>.json     # elimina un progetto
```

I dataset di esempio si trovano nella root del progetto (`sales_data.csv`).

### Git

```bash
git status                     # file modificati
git diff                       # modifiche non committate
git log --oneline -10          # ultimi commit
git add -A && git commit -m "descrizione"
git push origin main
```

### Diagnostica

```bash
docker compose logs -f          # log del server, utili per capire un errore ETL
docker compose ps               # container attivi
curl -I http://localhost:8080/etl-editor    # deve rispondere 200
```

Un errore 500 su `/etl-editor` o `/dashboard-editor` significa quasi sempre una
dipendenza mancante o un errore di import: controlla i log.

---

## 11. Test

I test Playwright hanno bisogno del codice applicativo **e** della cartella test,
perciò vanno eseguiti dentro Docker:

```bash
docker build -q -t pybi:test .
docker run --rm \
  -v "$PWD/tests:/app/tests:ro" \
  -v "$PWD/pybi_data:/app/data" \
  pybi:test sh -c "pip install --no-cache-dir -q pytest playwright \
    && playwright install --with-deps chromium \
    && python -m pytest tests/ -q"
```

I test E2E usano una cartella `DATA_DIR` temporanea e isolata, quindi non
toccano i tuoi progetti reali e non serve pulire nulla dopo un test.

Suite attuale: **190+ test**, di cui test di performance, E2E browser (Playwright), join, PostgreSQL, grafici, pivot table, auth/scheduler e storage. CI/CD automatizzata tramite GitHub Actions (`.github/workflows/ci.yml`).

> Attenzione: `pybi_data/` contiene i **dati reali** (progetti, CSV, database) ed
> è escluso da git. Non usare `rm -rf pybi_data/*` per fare pulizia: per i database
> di prova usa un percorso temporaneo.

---

## 12. Limitazioni note

- **Il Join accetta solo due input**: niente join a tre o più tabelle in un colpo.
  Puoi comunque concatenare più join in sequenza.
- **Fuori dal nodo Join, più ingressi vengono ignorati**: si usa solo il primo.
- **PostgreSQL non è esposto nella palette**: il connettore esiste e
  l'executor lo supporta, ma la UI offre solo csv, parquet e sqlite.
- **Il binding dashboard è in memoria**: dopo un riavvio del server le tabelle
  vanno ricalcolate con Execute Pipeline.
- **Le tabelle `duckdb` dell'ETL non sopravvivono al riavvio**: usa
  `Output Type = sqlite` se devi conservare il risultato.
- `pybi/storage/project_manager.py` (backend su SQLite) e
  `pybi/ui/components/charts.py` sono presenti ma non ancora collegati alle
  pagine.
- `pybi/auth/`, `pybi/datamodel/` e `pybi/server/` sono stub vuoti.

---

## 13. Prossimi passi suggeriti

1. Esporre il connettore **PostgreSQL** nella palette
2. Join a n tabelle e aggregazioni nella stessa trasformazione
3. Rendere persistente il binding del dashboard
4. Collegare il backend di storage su SQLite e la libreria grafica
