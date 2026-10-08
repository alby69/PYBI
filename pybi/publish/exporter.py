"""Publish exporter logic implementing Publisher ABC."""

import os
from typing import Optional
from pybi.core.interfaces import Publisher


class DashboardPublisher(Publisher):
    """Concrete Publisher implementation for static HTML and PDF dashboard exports."""

    def export_to_html(self, project_id: str, output_path: Optional[str] = None) -> str:
        out_path = output_path or f"export_{project_id}.html"
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>PyBI Dashboard - {project_id}</title>
</head>
<body>
    <h1>PyBI Exported Dashboard: {project_id}</h1>
    <div id="app">Static HTML Export</div>
</body>
</html>"""
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return out_path

    def export_to_pdf(self, project_id: str, output_path: Optional[str] = None) -> str:
        out_path = output_path or f"export_{project_id}.pdf"
        with open(out_path, "wb") as f:
            f.write(b"%PDF-1.4 Mock PDF Export for PyBI")
        return out_path
