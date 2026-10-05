"""Tests for new UI/UX components and features."""

import json
from pybi.core.history import HistoryManager
from pybi.export.dashboard_exporter import DashboardExporter
from pybi.ui.theme import NODE_COLORS, ThemeManager


def test_theme_colors():
    assert 'DataSource' in NODE_COLORS
    assert 'Filter' in NODE_COLORS
    assert NODE_COLORS['DataSource']['border'] == '#0284c7'


def test_theme_manager():
    tm = ThemeManager(dark_mode=False)
    assert not tm.is_dark
    tm.toggle()
    assert tm.is_dark


def test_history_manager():
    hm = HistoryManager(max_history=5)
    assert not hm.can_undo()
    assert not hm.can_redo()

    hm.push_state({'val': 1})
    hm.push_state({'val': 2})

    assert hm.can_undo()
    prev = hm.undo()
    assert prev == {'val': 1}
    assert hm.can_redo()

    nxt = hm.redo()
    assert nxt == {'val': 2}


def test_dashboard_exporter():
    layout = [
        {'i': 'w1', 'title': 'Revenue', 'type': 'kpi', 'value': '$100'}
    ]
    json_str = DashboardExporter.export_to_json(layout)
    parsed = json.loads(json_str)
    assert parsed[0]['title'] == 'Revenue'

    html_str = DashboardExporter.export_to_html("Test Dashboard", layout)
    assert "<title>Test Dashboard</title>" in html_str
    assert "Revenue" in html_str

    share_link = DashboardExporter.generate_share_link("proj123")
    assert share_link == "/viewer?project=proj123"
