import duckdb
import polars as pl

from pybi.core.events import ETL_EXECUTION_COMPLETED, EventBus, event_bus
from pybi.dashboard.binding import DataBinder
from pybi.etl.executor import ETLExecutor


def test_event_bus_subscribes_unsubscribes_and_publishes_payload():
    bus = EventBus()
    events = []
    handler = events.append

    bus.subscribe("test.event", handler)
    bus.subscribe("test.event", handler)
    bus.publish("test.event", value=42)
    bus.unsubscribe("test.event", handler)
    bus.publish("test.event", value=43)

    assert events == [{"name": "test.event", "value": 42}]


def test_etl_executor_publishes_project_scoped_completion():
    events = []
    handler = events.append
    event_bus.subscribe(ETL_EXECUTION_COMPLETED, handler)
    try:
        result = ETLExecutor(project_id="project-a").execute({})
    finally:
        event_bus.unsubscribe(ETL_EXECUTION_COMPLETED, handler)

    assert result.status == "success"
    assert events[0]["project_id"] == "project-a"
    assert events[0]["status"] == "success"


def test_dashboard_binder_registers_successful_etl_outputs():
    connection = duckdb.connect(":memory:")
    binder = DataBinder(connection, observe_etl_events=True)
    handler = binder._on_etl_execution_completed
    try:
        frame = pl.DataFrame({"value": [7]})
        event_bus.publish(
            ETL_EXECUTION_COMPLETED,
            project_id="project-a",
            status="success",
            output_tables={"etl_output": frame},
            error=None,
        )
        assert binder.get_source_data("etl_output").to_dicts() == [{"value": 7}]
    finally:
        event_bus.unsubscribe(ETL_EXECUTION_COMPLETED, handler)
        connection.close()
