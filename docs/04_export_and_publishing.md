# 📄 Export & Publishing Engine Specifications

## 1. Overview
The **Publishing & Export Engine (`pybi.export`)** converts dynamic dashboards, semantic metrics, and visual layouts into frozen, reproducible artifacts (PDF, HTML, Markdown, CSV).

Key capabilities:
- **Immutable Snapshot Metadata (`snapshot.json`):** Tracks `export_id`, timestamp, project version, and a SHA-256 hash of active filter rules (`active_filters_hash`).
- **Jinja2 Templating:** Custom report templates with dynamic variable interpolation.
- **Async Execution:** Asynchronous background processing for non-blocking report rendering.

---

## 2. Snapshot Metadata Schema (`snapshot.json`)

```json
{
  "export_id": "exp_a1b2c3d4e5f6",
  "timestamp": "2026-10-08T12:00:00.000000+00:00",
  "project_id": "sales_dashboard",
  "project_version": "1.0.0",
  "active_filters_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "active_filters": {
    "sales.region": {
      "table": "sales",
      "column": "region",
      "values": ["Europe", "North America"],
      "operator": "IN"
    }
  },
  "source_files_list": ["sales_data.csv"],
  "format": "pdf",
  "template_id": "report_dati.html"
}
```

---

## 3. Export REST Endpoints

- `POST /api/v1/projects/{project_id}/export`: Submit export job.
- `POST /api/v1/projects/{project_id}/export/pdf`: PDF generation shortcut.
- `POST /api/v1/projects/{project_id}/export/data`: CSV extract shortcut.
- `GET /api/v1/exports/{export_id}/status`: Poll export status.
- `GET /api/v1/exports/{export_id}/download`: Download generated file artifact.
