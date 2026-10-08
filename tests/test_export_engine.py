"""Tests for Phase 5 Publishing & Export Engine."""

import time
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from pybi.api.main import app
from pybi.dashboard.filter_context import FilterContext
from pybi.export_engine import (
    ExportEngine,
    default_export_engine,
    create_snapshot,
    hash_filter_context,
    bind_filter_context,
)


def test_hash_filter_context_determinism():
    """Verify SHA-256 filter context hashing is deterministic and order-independent."""
    ctx1 = FilterContext()
    ctx1.set_filter("sales", "region", ["Europe", "North America"])
    ctx1.set_filter("sales", "year", [2025])

    ctx2 = FilterContext()
    ctx2.set_filter("sales", "year", [2025])
    ctx2.set_filter("sales", "region", ["North America", "Europe"])

    h1 = hash_filter_context(ctx1)
    h2 = hash_filter_context(ctx2)

    assert isinstance(h1, str)
    assert len(h1) == 64  # SHA-256 hex length
    assert h1 == h2


def test_create_snapshot_metadata():
    """Verify snapshot generation contains all required immutable metadata keys."""
    ctx = FilterContext()
    ctx.set_filter("orders", "country", ["Italy"])

    snap = create_snapshot(
        project_id="test_proj",
        project_version="1.2.0",
        filter_context=ctx,
        source_files=["orders.csv"],
        export_format="pdf",
        template_id="report_dati.html",
        ai_prompt="Generate executive summary for Italy",
    )

    assert snap["project_id"] == "test_proj"
    assert snap["project_version"] == "1.2.0"
    assert snap["format"] == "pdf"
    assert snap["active_filters_hash"] is not None
    assert "orders.country" in snap["active_filters"]
    assert snap["source_files_list"] == ["orders.csv"]
    assert snap["ai_compilation_prompt"] == "Generate executive summary for Italy"


def test_bind_filter_context_payload():
    """Verify bind_filter_context correctly applies filters and filters table rows."""
    ctx = FilterContext()
    ctx.set_filter("sales", "region", ["EU"])

    payload = {
        "title": "Sales Report",
        "tables": {
            "sales": [
                {"region": "EU", "amount": 100},
                {"region": "US", "amount": 200},
                {"region": "EU", "amount": 150},
            ]
        }
    }

    bound = bind_filter_context(payload, ctx)
    assert "active_filters" in bound
    assert len(bound["active_filters"]) == 1
    assert bound["active_filters"][0]["table"] == "sales"
    assert len(bound["tables"]["sales"]) == 2
    assert all(r["region"] == "EU" for r in bound["tables"]["sales"])


def test_export_engine_render_formats(tmp_path):
    """Verify ExportEngine renders HTML, Markdown, CSV, and PDF correctly."""
    engine = ExportEngine(exports_dir=str(tmp_path))

    ctx = FilterContext()
    ctx.set_filter("kpi", "category", ["A"])

    payload = {
        "title": "Unit Test Report",
        "widgets": [{"i": "w1", "title": "Total Revenue", "type": "kpi", "value": "$10,000"}],
        "tables": {
            "kpi": [{"category": "A", "val": 50}, {"category": "B", "val": 30}]
        }
    }

    # 1. HTML
    job_id_html = engine.submit_export_job(
        project_id="p1",
        payload=payload,
        filter_context=ctx,
        export_format="html",
        template_id="report_dati.html",
    )
    time.sleep(0.5)
    status_html = engine.get_job_status(job_id_html)
    assert status_html["status"] == "completed"
    assert Path(status_html["file_path"]).exists()

    # 2. Markdown
    job_id_md = engine.submit_export_job(
        project_id="p1",
        payload=payload,
        filter_context=ctx,
        export_format="md",
        template_id="documento_knowledge.md",
    )
    time.sleep(0.5)
    status_md = engine.get_job_status(job_id_md)
    assert status_md["status"] == "completed"
    assert Path(status_md["file_path"]).exists()

    # 3. CSV
    job_id_csv = engine.submit_export_job(
        project_id="p1",
        payload=payload,
        filter_context=ctx,
        export_format="csv",
    )
    time.sleep(0.5)
    status_csv = engine.get_job_status(job_id_csv)
    assert status_csv["status"] == "completed"
    assert Path(status_csv["file_path"]).exists()

    # 4. PDF
    job_id_pdf = engine.submit_export_job(
        project_id="p1",
        payload=payload,
        filter_context=ctx,
        export_format="pdf",
    )
    time.sleep(0.5)
    status_pdf = engine.get_job_status(job_id_pdf)
    assert status_pdf["status"] == "completed"
    assert Path(status_pdf["file_path"]).exists()


def test_export_api_endpoints():
    """Verify FastAPI export endpoints for submitting, status polling, and downloading."""
    client = TestClient(app)

    req_payload = {
        "format": "html",
        "template_id": "report_dati.html",
        "filter_context": {"sales.region": ["EU"]},
        "ai_compilation_prompt": "Test AI Prompt",
        "payload": {
            "title": "API Test Dashboard",
            "widgets": [{"title": "Card 1", "type": "kpi", "value": "100"}]
        }
    }

    # Submit job
    res = client.post("/api/projects/api_project/export", json=req_payload)
    assert res.status_code == 200
    data = res.json()
    assert "export_id" in data
    export_id = data["export_id"]

    # Poll status
    time.sleep(0.5)
    status_res = client.get(f"/api/exports/{export_id}/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["export_id"] == export_id
    assert status_data["status"] == "completed"

    # Download file
    dl_res = client.get(f"/api/exports/{export_id}/download")
    assert dl_res.status_code == 200
    assert "API Test Dashboard" in dl_res.text
