import pytest


def test_post_etl_preview_success(client):
    payload = {
        "source_table": "sales",
        "steps": [
            {
                "step_id": "step_1",
                "step_type": "filter_rows",
                "parameters": {"column": "price", "operator": ">=", "value": "100"}
            }
        ],
        "limit": 10
    }

    response = client.post("/api/v1/projects/proj_001/etl/preview", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "columns" in data
    assert "rows" in data
    assert data["total_rows"] == 2
    assert len(data["rows"]) == 2


def test_post_etl_preview_invalid_sql_expression(client):
    payload = {
        "source_table": "sales",
        "steps": [
            {
                "step_id": "step_bad",
                "step_type": "add_custom_column",
                "parameters": {"new_column": "bad_col", "expression": "price + INVALID_SYNTAX_((("}
            }
        ]
    }

    response = client.post("/api/v1/projects/proj_001/etl/preview", json=payload)
    assert response.status_code == 400
    assert "syntax error" in response.json()["detail"].lower() or "errore" in response.json()["detail"].lower() or "error" in response.json()["detail"].lower()


def test_save_and_get_etl_query(client):
    query_payload = {
        "query_name": "Cleaned Sales",
        "source_table": "sales",
        "steps": [
            {
                "step_id": "s1",
                "step_type": "rename_column",
                "parameters": {"old_name": "price", "new_name": "unit_price"}
            }
        ]
    }

    # Save Query
    save_resp = client.post("/api/v1/projects/proj_001/etl/queries", json=query_payload)
    assert save_resp.status_code == 201
    created_query = save_resp.json()
    query_id = created_query["query_id"]

    # Fetch Saved Query
    get_resp = client.get(f"/api/v1/projects/proj_001/etl/queries/{query_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["query_name"] == "Cleaned Sales"
    assert len(get_resp.json()["steps"]) == 1


def test_api_empty_result_set(client):
    payload = {
        "source_table": "sales",
        "steps": [
            {
                "step_id": "step_empty",
                "step_type": "filter_rows",
                "parameters": {"column": "price", "operator": ">", "value": "999999"}
            }
        ]
    }

    response = client.post("/api/v1/projects/proj_001/etl/preview", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["rows"] == []
    assert data["total_rows"] == 0
    assert "product" in data["columns"]
    assert "price" in data["columns"]


def test_api_limit_clamp_to_1000(client):
    payload = {
        "source_table": "sales",
        "steps": [],
        "limit": 2000
    }

    response = client.post("/api/v1/projects/proj_001/etl/preview", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["rows"]) <= 1000


def test_api_special_characters_handling(client):
    payload = {
        "source_table": "sales",
        "steps": [
            {
                "step_id": "s1",
                "step_type": "add_custom_column",
                "parameters": {"new_column": "Total Price ($)", "expression": "price * qty"}
            }
        ]
    }

    response = client.post("/api/v1/projects/proj_001/etl/preview", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "Total Price ($)" in data["columns"]


def test_api_data_type_casting_error(client):
    payload = {
        "source_table": "sales",
        "steps": [
            {
                "step_id": "s1",
                "step_type": "change_type",
                "parameters": {"column": "product", "new_type": "INTEGER"}
            }
        ]
    }

    response = client.post("/api/v1/projects/proj_001/etl/preview", json=payload)
    assert response.status_code == 400
    assert "errore" in response.json()["detail"].lower() or "error" in response.json()["detail"].lower() or "conversion" in response.json()["detail"].lower()
