import inspect

from backend.api.v1.etl import get_etl_dag, preview_node_output, save_etl_dag
from backend.api.v1.models import ETLDAGSchema, ETLQuery, ETLStep


def test_legacy_etl_handlers_keep_synchronous_contract():
    assert not inspect.iscoroutinefunction(get_etl_dag)
    assert not inspect.iscoroutinefunction(save_etl_dag)
    assert not inspect.iscoroutinefunction(preview_node_output)


def test_legacy_etl_models_serialize_historical_field_names():
    step = ETLStep(step_id="step_1", step_type="filter")

    assert step.model_dump() == {
        "id": "step_1",
        "name": None,
        "operation": "filter",
        "params": {},
    }

    query = ETLQuery(steps=[step])
    dag = ETLDAGSchema(steps=[step])
    assert query.model_dump()["steps"][0]["id"] == "step_1"
    assert query.model_dump()["steps"][0]["operation"] == "filter"
    assert dag.model_dump()["steps"][0]["id"] == "step_1"
    assert dag.model_dump()["steps"][0]["operation"] == "filter"
