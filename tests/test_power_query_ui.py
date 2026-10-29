"""Tests for Power Query Editor Vue 3 components and Python wrapper integration."""

import os
from pybi.frontend.components.power_query.power_query_editor import PowerQueryEditor
from pybi.ui.components.power_query import PowerQueryEditor as UIEditorWrapper


def test_power_query_vue_component_files_exist():
    """Verify all 5 Power Query Editor Vue 3 components exist in the directory structure."""
    base_dir = os.path.join("pybi", "frontend", "components", "power_query")
    expected_files = [
        "PowerQueryRibbon.vue",
        "QueriesPane.vue",
        "DataGridPreview.vue",
        "AppliedStepsPanel.vue",
        "CustomColumnModal.vue",
        "FormulaBar.vue",
        "PowerQueryEditor.vue",
        "index.js",
    ]
    for fname in expected_files:
        fpath = os.path.join(base_dir, fname)
        assert os.path.exists(fpath), f"Missing expected Power Query Vue file: {fpath}"


def test_power_query_python_editor_wrapper():
    """Verify PowerQueryEditor Python wrapper element initialization and properties."""
    tables = ["sales_data.csv", "customers.parquet"]
    editor = PowerQueryEditor(tables=tables, selected_table="sales_data.csv")

    assert editor._tables == tables
    assert editor._selected_table == "sales_data.csv"
    assert "sales_data.csv" in editor._applied_steps_by_table

    # Test selecting a table
    editor.set_selected_table("customers.parquet")
    assert editor._selected_table == "customers.parquet"

    # Test updating steps
    new_steps = [{"id": "step_1", "operation": "filter", "name": "EU filter", "params": {}}]
    editor.update_steps("customers.parquet", new_steps)
    assert editor._applied_steps_by_table["customers.parquet"] == new_steps

    # Test re-exported wrapper class
    assert UIEditorWrapper is PowerQueryEditor


def test_power_query_vue_ribbon_structure():
    """Read PowerQueryRibbon.vue and verify 4 tabs (Home, Transform, Add Column, View)."""
    fpath = os.path.join("pybi", "frontend", "components", "power_query", "PowerQueryRibbon.vue")
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "activeTab" in content
    assert "Home" in content
    assert "Transform" in content
    assert "Add Column" in content
    assert "View" in content
    assert "add-custom-column" in content
    assert "choose-columns" in content


def test_power_query_queries_pane_structure():
    """Read QueriesPane.vue and verify collapsible sidebar and context menu actions."""
    fpath = os.path.join("pybi", "frontend", "components", "power_query", "QueriesPane.vue")
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "isCollapsed" in content
    assert "Duplicate" in content
    assert "Reference" in content
    assert "Rename" in content
    assert "Delete" in content
    assert "Move to Group" in content


def test_power_query_data_grid_preview_structure():
    """Read DataGridPreview.vue and verify header data type icons and scrolling behavior."""
    fpath = os.path.join("pybi", "frontend", "components", "power_query", "DataGridPreview.vue")
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "getTypeIcon" in content
    assert "ABC" in content
    assert "123" in content
    assert "1.2" in content
    assert "overflow-x-auto" in content
    assert "overflow-y-auto" in content


def test_power_query_applied_steps_panel_structure():
    """Read AppliedStepsPanel.vue and verify Properties, Applied Steps list, trash icon, and gear icon."""
    fpath = os.path.join("pybi", "frontend", "components", "power_query", "AppliedStepsPanel.vue")
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Properties" in content
    assert "Applied Steps" in content
    assert "deleteStep" in content or "removeStep" in content
    assert "openStepSettings" in content or "edit-step-settings" in content
    assert "activeStepIndex" in content


def test_power_query_custom_column_modal_structure():
    """Read CustomColumnModal.vue and verify formula editor, practical examples, and function catalog."""
    fpath = os.path.join("pybi", "frontend", "components", "power_query", "CustomColumnModal.vue")
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Practical Expression Examples" in content
    assert "CONCAT" in content
    assert "CASE WHEN" in content
    assert "functionCatalog" in content
    assert "newColumnName" in content
