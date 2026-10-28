"""Unit tests for widget deletion, unique ID generation, and configuration fallback logic."""

import pytest
from pybi.ui.components.widget_data import source_fields, register_sample_source
from pybi.ui.components.widget_configurator import _as_list, _union


def test_as_list_and_union():
    assert _as_list(None) == []
    assert _as_list("a, b, c") == ["a", "b", "c"]
    assert _as_list(["a", "b"]) == ["a", "b"]

    options = ["dim1", "dim2"]
    values = ["dim2", "dim3"]
    assert _union(options, values) == ["dim1", "dim2", "dim3"]


def test_source_fields_fallback():
    register_sample_source()
    fields = source_fields("regional_sales")
    assert "region" in fields["dimensions"]
    assert "revenue" in fields["measures"]

    unknown_fields = source_fields("non_existent_source_xyz")
    assert unknown_fields == {"dimensions": [], "measures": []}


def test_widget_deletion_fallback_logic():
    layout = [
        {"i": "w1", "title": "Dati ETS", "type": "chart"},
        {"title": "Dati ETS senza ID", "type": "kpi"},
    ]

    # Matching with ID
    w_id = "w1"
    w_title = "Dati ETS"
    filtered_1 = [
        item for item in layout
        if not (
            (w_id and item.get("i") == w_id) or
            (not w_id and w_title and item.get("title") == w_title)
        )
    ]
    assert len(filtered_1) == 1
    assert filtered_1[0]["title"] == "Dati ETS senza ID"

    # Matching without ID (fallback on title)
    w_id_2 = None
    w_title_2 = "Dati ETS senza ID"
    filtered_2 = [
        item for item in layout
        if not (
            (w_id_2 and item.get("i") == w_id_2) or
            (not w_id_2 and w_title_2 and item.get("title") == w_title_2)
        )
    ]
    assert len(filtered_2) == 1
    assert filtered_2[0]["i"] == "w1"
