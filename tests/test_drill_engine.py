"""Unit tests for Drill-Through engine and navigation stack."""

from pybi.ui.components.drill_engine import DrillEngine, default_drill_engine


def test_drill_engine_push_and_pop():
    engine = DrillEngine()
    assert engine.drill_context is None
    assert len(engine.drill_history) == 0

    # 1. Set drill context
    engine.set_drill_context("report_details", {"region": "Europe"})
    assert engine.drill_context["target_report"] == "report_details"
    assert engine.drill_context["filters"] == {"region": "Europe"}

    # 2. Drill deeper
    engine.set_drill_context("report_deep_details", {"region": "Europe", "country": "Italy"})
    assert len(engine.drill_history) == 1
    assert engine.drill_context["target_report"] == "report_deep_details"

    # 3. Pop back
    prev = engine.pop_drill_context()
    assert prev is not None
    assert engine.drill_context["target_report"] == "report_details"
    assert engine.drill_context["filters"] == {"region": "Europe"}

    # 4. Clear drill context
    engine.clear()
    assert engine.drill_context is None
    assert len(engine.drill_history) == 0
