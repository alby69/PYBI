"""Unit tests for pybi.ui.table_utils preview table helpers."""

from pybi.ui.table_utils import build_preview_table, pick_row_key


def test_pick_row_key_prefers_id_column():
    columns = ["id", "region", "sales"]
    rows = [
        {"id": 1, "region": "EU", "sales": 10},
        {"id": 2, "region": "US", "sales": 20},
    ]
    assert pick_row_key(columns, rows) == "id"


def test_pick_row_key_falls_back_to_first_unique_column():
    columns = ["region", "sales"]
    rows = [{"region": "EU", "sales": 10}, {"region": "US", "sales": 20}]
    assert pick_row_key(columns, rows) == "region"


def test_pick_row_key_skips_duplicated_column():
    columns = ["region", "sales"]
    rows = [{"region": "EU", "sales": 10}, {"region": "EU", "sales": 20}]
    assert pick_row_key(columns, rows) == "sales"


def test_pick_row_key_returns_none_when_no_column_is_unique():
    columns = ["region", "sales"]
    rows = [{"region": "EU", "sales": 10}, {"region": "EU", "sales": 10}]
    assert pick_row_key(columns, rows) is None


def test_pick_row_key_returns_none_when_candidate_has_nulls():
    columns = ["region"]
    rows = [{"region": "EU"}, {"region": None}]
    assert pick_row_key(columns, rows) is None


def test_pick_row_key_ignores_id_when_missing_in_a_row():
    columns = ["id", "region"]
    rows = [{"region": "EU"}, {"id": 2, "region": "US"}]
    assert pick_row_key(columns, rows) == "region"


def test_pick_row_key_handles_empty_input():
    assert pick_row_key([], []) is None
    assert pick_row_key(["region"], []) is None


def test_build_preview_table_from_dataframe():
    import polars as pl

    df = pl.DataFrame({"region": ["EU", "US"], "sales": [10, 20]})
    table_args = build_preview_table(df)
    assert table_args["row_key"] == "region"
    assert table_args["rows"] == [{"region": "EU", "sales": 10}, {"region": "US", "sales": 20}]
    assert [column["field"] for column in table_args["columns"]] == ["region", "sales"]
    assert all(column["sortable"] for column in table_args["columns"])


def test_build_preview_table_grouped_output_without_unique_key():
    import polars as pl

    df = pl.DataFrame({"region": ["EU", "EU"], "sales": [10, 10]})
    table_args = build_preview_table(df)
    assert table_args["row_key"] is None


def test_build_preview_table_handles_empty_dataframe():
    import polars as pl

    table_args = build_preview_table(pl.DataFrame({"region": [], "sales": []}))
    assert table_args["rows"] == []
    assert table_args["row_key"] is None
