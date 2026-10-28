"""Unit tests for WYSIWYG PDF/HTML export engine and snapshot filter hash validation."""

from pybi.export.engine import default_export_engine
from pybi.export.snapshot import create_snapshot, hash_filter_context


def test_wysiwyg_html_render_grid_classes():
    payload = {
        "title": "WYSIWYG Test Report",
        "project_id": "proj_wysiwyg",
        "widgets": [
            {"i": "w1", "title": "Sales KPI", "type": "kpi", "value": "$500,000", "w": 4, "h": 3},
            {"i": "w2", "title": "Regional Chart", "type": "chart", "value": "Active", "w": 8, "h": 3}
        ]
    }

    snapshot = create_snapshot(
        project_id="proj_wysiwyg",
        filter_context={"region": ["Europe", "Asia"]}
    )
    payload["snapshot"] = snapshot

    html = default_export_engine.render_html(payload, "report_dati.html")

    assert "widget-w4" in html
    assert "widget-w8" in html
    assert "WYSIWYG Test Report" in html
    assert "@page" in html
    assert "counter(page)" in html


def test_snapshot_sha256_hash_immutability():
    ctx1 = {"region": ["Europe", "North America"], "year": "2024"}
    ctx2 = {"region": ["Europe", "North America"], "year": "2024"}
    ctx3 = {"region": ["Europe"], "year": "2024"}

    hash1 = hash_filter_context(ctx1)
    hash2 = hash_filter_context(ctx2)
    hash3 = hash_filter_context(ctx3)

    assert len(hash1) == 64
    assert hash1 == hash2
    assert hash1 != hash3
