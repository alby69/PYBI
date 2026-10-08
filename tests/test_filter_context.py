import pytest
import duckdb
from model.schema import Table, Column, Relationship
from model.measures import ModelEngine, Measure
from dashboard.filter_context import FilterContext

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def duckdb_conn():
    """Crea una connessione DuckDB in-memory con dati di test."""
    conn = duckdb.connect()

    # Tabella Fatti: Sales
    conn.execute("""
        CREATE TABLE sales (
            sale_id INTEGER,
            region VARCHAR,
            product VARCHAR,
            amount DOUBLE,
            quantity INTEGER
        )
    """)
    conn.execute("""
        INSERT INTO sales VALUES
        (1, 'Nord', 'Laptop', 1000.0, 2),
        (2, 'Nord', 'Mouse', 50.0, 10),
        (3, 'Sud', 'Laptop', 1200.0, 3),
        (4, 'Sud', 'Mouse', 60.0, 12),
        (5, 'Centro', 'Laptop', 1100.0, 2)
    """)

    # Tabella Fatti: Target
    conn.execute("""
        CREATE TABLE target (
            region VARCHAR,
            target_amount DOUBLE
        )
    """)
    conn.execute("""
        INSERT INTO target VALUES
        ('Nord', 2000.0),
        ('Sud', 2500.0),
        ('Centro', 1500.0)
    """)

    yield conn
    conn.close()

@pytest.fixture
def model_engine(duckdb_conn):
    """Crea un ModelEngine con tabelle e misure di test."""
    engine = ModelEngine(duckdb_conn)

    # Registra tabella sales
    sales_table = Table(
        name="sales",
        columns=[
            Column("sale_id", "INTEGER"),
            Column("region", "VARCHAR"),
            Column("product", "VARCHAR"),
            Column("amount", "DOUBLE"),
            Column("quantity", "INTEGER")
        ],
        relationships=[]
    )
    engine.register_table(sales_table)

    # Registra misure
    engine.register_measure(Measure("Total Sales", "sales", "SUM(amount)"))
    engine.register_measure(Measure("Avg Quantity", "sales", "AVERAGE(quantity)"))
    engine.register_measure(Measure("Sales per Unit", "sales", "DIVIDE(SUM(amount), SUM(quantity))"))

    return engine

@pytest.fixture
def filter_context():
    """Crea un FilterContext vuoto."""
    return FilterContext()

# ============================================================================
# TEST: FilterContext - Gestione Stato Filtri
# ============================================================================

def test_set_single_filter(filter_context):
    """Test: impostare un filtro su una singola colonna."""
    filter_context.set_filter("sales", "region", ["Nord"])

    filters = filter_context.get_active_filters_for_table("sales")
    assert len(filters) == 1
    assert filters[0].column == "region"
    assert filters[0].values == ["Nord"]

def test_set_multiple_filters_same_table(filter_context):
    """Test: impostare più filtri sulla stessa tabella."""
    filter_context.set_filter("sales", "region", ["Nord"])
    filter_context.set_filter("sales", "product", ["Laptop"])

    filters = filter_context.get_active_filters_for_table("sales")
    assert len(filters) == 2

def test_clear_filter(filter_context):
    """Test: rimuovere un filtro specifico."""
    filter_context.set_filter("sales", "region", ["Nord"])
    filter_context.set_filter("sales", "product", ["Laptop"])

    filter_context.clear_filter("sales", "region")

    filters = filter_context.get_active_filters_for_table("sales")
    assert len(filters) == 1
    assert filters[0].column == "product"

def test_overwrite_filter(filter_context):
    """Test: sovrascrivere un filtro esistente sulla stessa colonna."""
    filter_context.set_filter("sales", "region", ["Nord"])
    filter_context.set_filter("sales", "region", ["Sud", "Centro"])

    filters = filter_context.get_active_filters_for_table("sales")
    assert len(filters) == 1
    assert filters[0].values == ["Sud", "Centro"]

# ============================================================================
# TEST: FilterContext - Generazione SQL WHERE
# ============================================================================

def test_where_clause_single_string_filter(filter_context, model_engine):
    """Test: generazione WHERE con filtro su stringa."""
    filter_context.set_filter("sales", "region", ["Nord"])

    where = filter_context.to_sql_where(model_engine.tables["sales"])
    assert "WHERE" in where
    assert "region IN ('Nord')" in where

def test_where_clause_multiple_values(filter_context, model_engine):
    """Test: generazione WHERE con filtro su più valori."""
    filter_context.set_filter("sales", "region", ["Nord", "Sud"])

    where = filter_context.to_sql_where(model_engine.tables["sales"])
    assert "region IN ('Nord', 'Sud')" in where

def test_where_clause_numeric_filter(filter_context, model_engine):
    """Test: generazione WHERE con filtro su numerico."""
    filter_context.set_filter("sales", "quantity", [5])

    where = filter_context.to_sql_where(model_engine.tables["sales"])
    assert "quantity IN (5)" in where

def test_where_clause_empty_context(filter_context, model_engine):
    """Test: contesto vuoto genera WHERE vuota."""
    where = filter_context.to_sql_where(model_engine.tables["sales"])
    assert where == ""

def test_where_clause_multiple_filters(filter_context, model_engine):
    """Test: generazione WHERE con più filtri concatenati con AND."""
    filter_context.set_filter("sales", "region", ["Nord"])
    filter_context.set_filter("sales", "product", ["Laptop"])

    where = filter_context.to_sql_where(model_engine.tables["sales"])
    assert "AND" in where
    assert "region IN ('Nord')" in where
    assert "product IN ('Laptop')" in where

# ============================================================================
# TEST: ModelEngine - Valutazione Misure
# ============================================================================

def test_evaluate_sum_without_filter(model_engine):
    """Test: valutazione SUM senza filtri."""
    result = model_engine.evaluate_measure("Total Sales", FilterContext())
    assert result == 3410.0  # 1000 + 50 + 1200 + 60 + 1100

def test_evaluate_sum_with_filter(model_engine, filter_context):
    """Test: valutazione SUM con filtro attivo."""
    filter_context.set_filter("sales", "region", ["Nord"])
    result = model_engine.evaluate_measure("Total Sales", filter_context)
    assert result == 1050.0  # 1000 + 50

def test_evaluate_average_without_filter(model_engine):
    """Test: valutazione AVERAGE senza filtri."""
    result = model_engine.evaluate_measure("Avg Quantity", FilterContext())
    assert result == 5.8  # (2 + 10 + 3 + 12 + 2) / 5

def test_evaluate_average_with_filter(model_engine, filter_context):
    """Test: valutazione AVERAGE con filtro attivo."""
    filter_context.set_filter("sales", "region", ["Sud"])
    result = model_engine.evaluate_measure("Avg Quantity", filter_context)
    assert result == 7.5  # (3 + 12) / 2

def test_evaluate_divide_without_filter(model_engine):
    """Test: valutazione DIVIDE senza filtri (gestione divisione per zero)."""
    result = model_engine.evaluate_measure("Sales per Unit", FilterContext())
    # 3410 / 29 = 117.586...
    assert abs(result - 117.586) < 0.01

def test_evaluate_divide_with_filter(model_engine, filter_context):
    """Test: valutazione DIVIDE con filtro attivo."""
    filter_context.set_filter("sales", "region", ["Nord"])
    result = model_engine.evaluate_measure("Sales per Unit", filter_context)
    # 1050 / 12 = 87.5
    assert result == 87.5

# ============================================================================
# TEST: FilterContext - Notifica Listener (Cross-Filtering)
# ============================================================================

def test_listener_notified_on_filter_change(filter_context):
    """Test: i listener vengono notificati quando un filtro cambia."""
    notifications = []

    def mock_listener(active_filters):
        notifications.append(len(active_filters))

    filter_context.subscribe(mock_listener)

    filter_context.set_filter("sales", "region", ["Nord"])
    assert len(notifications) == 1
    assert notifications[0] == 1

    filter_context.set_filter("sales", "product", ["Laptop"])
    assert len(notifications) == 2
    assert notifications[1] == 2

def test_listener_notified_on_filter_clear(filter_context):
    """Test: i listener vengono notificati quando un filtro viene rimosso."""
    notifications = []

    def mock_listener(active_filters):
        notifications.append(len(active_filters))

    filter_context.subscribe(mock_listener)

    filter_context.set_filter("sales", "region", ["Nord"])
    filter_context.clear_filter("sales", "region")

    assert len(notifications) == 2
    assert notifications[1] == 0

def test_multiple_listeners(filter_context):
    """Test: più listener vengono tutti notificati."""
    notifications_1 = []
    notifications_2 = []

    filter_context.subscribe(lambda f: notifications_1.append(len(f)))
    filter_context.subscribe(lambda f: notifications_2.append(len(f)))

    filter_context.set_filter("sales", "region", ["Nord"])

    assert len(notifications_1) == 1
    assert len(notifications_2) == 1

# ============================================================================
# TEST: Edge Cases
# ============================================================================

def test_filter_with_special_characters(filter_context, model_engine):
    """Test: gestione valori con caratteri speciali (es. apostrofi)."""
    filter_context.set_filter("sales", "region", ["Nord-Ovest"])

    where = filter_context.to_sql_where(model_engine.tables["sales"])
    assert "region IN ('Nord-Ovest')" in where

def test_evaluate_measure_nonexistent(model_engine):
    """Test: valutazione di una misura inesistente deve sollevare errore."""
    with pytest.raises(KeyError):
        model_engine.evaluate_measure("Nonexistent Measure", FilterContext())

def test_filter_context_isolation(filter_context):
    """Test: filtri su tabelle diverse non interferiscono."""
    filter_context.set_filter("sales", "region", ["Nord"])
    filter_context.set_filter("target", "region", ["Sud"])

    sales_filters = filter_context.get_active_filters_for_table("sales")
    target_filters = filter_context.get_active_filters_for_table("target")

    assert len(sales_filters) == 1
    assert len(target_filters) == 1
    assert sales_filters[0].values == ["Nord"]
    assert target_filters[0].values == ["Sud"]
