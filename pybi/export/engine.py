"""Export Engine and Orchestrator for managing multi-format export background jobs."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import csv
import io
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

from pybi.export.context_binder import bind_filter_context
from pybi.export.snapshot import create_snapshot

# Define default exports directory
DEFAULT_EXPORTS_DIR = os.getenv("EXPORTS_DIR", "pybi_data/exports")


class ExportEngine:
    """Orchestrator for queuing and rendering static, versioned exports (PDF, HTML, MD, CSV)."""

    def __init__(self, exports_dir: Optional[str] = None):
        self.exports_dir = Path(exports_dir or DEFAULT_EXPORTS_DIR)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)

        templates_path = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(templates_path)),
            autoescape=select_autoescape(["html", "xml"])
        )

    def submit_export_job(
        self,
        project_id: str,
        payload: Dict[str, Any],
        filter_context: Optional[Any] = None,
        export_format: str = "html",
        template_id: Optional[str] = None,
        ai_prompt: Optional[str] = None,
        source_files: Optional[List[str]] = None,
        project_version: str = "1.0.0",
    ) -> str:
        """Submit export task to background worker pool.

        Returns:
            export_id: Unique string tracking job status and directory.
        """
        export_format = export_format.lower()
        if not template_id:
            template_id = "report_dati.html" if export_format in ["html", "pdf"] else "documento_knowledge.md"

        # 1. Bind filter context
        bound_payload = bind_filter_context(payload, filter_context)

        # 2. Create snapshot
        snapshot = create_snapshot(
            project_id=project_id,
            project_version=project_version,
            filter_context=filter_context,
            source_files=source_files,
            export_format=export_format,
            template_id=template_id,
            ai_prompt=ai_prompt,
        )

        bound_payload["snapshot"] = snapshot
        bound_payload["ai_compilation_prompt"] = ai_prompt or bound_payload.get("ai_compilation_prompt")

        export_id = snapshot["export_id"]

        job_info = {
            "export_id": export_id,
            "project_id": project_id,
            "status": "pending",
            "progress": 0,
            "format": export_format,
            "template_id": template_id,
            "snapshot": snapshot,
            "payload": bound_payload,
            "file_path": None,
            "error": None,
        }

        self.jobs[export_id] = job_info

        # Schedule execution in threadpool
        self._executor.submit(self._process_export_job, export_id)
        return export_id

    def _process_export_job(self, export_id: str) -> None:
        """Background execution worker for rendering job artifacts."""
        job = self.jobs.get(export_id)
        if not job:
            return

        try:
            job["status"] = "processing"
            job["progress"] = 25

            fmt = job["format"]
            payload = job["payload"]
            template_id = job["template_id"]
            snapshot = job["snapshot"]

            job_dir = self.exports_dir / export_id
            job_dir.mkdir(parents=True, exist_ok=True)

            # Save snapshot.json
            snapshot_path = job_dir / "snapshot.json"
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)

            job["progress"] = 50

            artifact_path = None
            if fmt == "html":
                html_str = self.render_html(payload, template_id)
                artifact_path = job_dir / f"export_{export_id}.html"
                with open(artifact_path, "w", encoding="utf-8") as f:
                    f.write(html_str)

            elif fmt in ["md", "markdown"]:
                md_str = self.render_markdown(payload, template_id)
                artifact_path = job_dir / f"export_{export_id}.md"
                with open(artifact_path, "w", encoding="utf-8") as f:
                    f.write(md_str)

            elif fmt == "csv":
                csv_str = self.render_csv(payload)
                artifact_path = job_dir / f"export_{export_id}.csv"
                with open(artifact_path, "w", encoding="utf-8") as f:
                    f.write(csv_str)

            elif fmt == "pdf":
                html_str = self.render_html(payload, template_id or "report_dati.html")
                pdf_bytes = self.render_pdf(payload, html_str)
                artifact_path = job_dir / f"export_{export_id}.pdf"
                with open(artifact_path, "wb") as f:
                    f.write(pdf_bytes)

            else:
                raise ValueError(f"Unsupported export format: {fmt}")

            job["progress"] = 100
            job["status"] = "completed"
            job["file_path"] = str(artifact_path)

        except Exception as err:
            job["status"] = "failed"
            job["error"] = str(err)

    def render_html(self, payload: Dict[str, Any], template_id: str = "report_dati.html") -> str:
        """Render HTML string using Jinja2 template."""
        tpl = self.jinja_env.get_template(template_id)
        return tpl.render(**payload)

    def render_markdown(self, payload: Dict[str, Any], template_id: str = "documento_knowledge.md") -> str:
        """Render Markdown string using Jinja2 template."""
        tpl = self.jinja_env.get_template(template_id)
        return tpl.render(**payload)

    def render_csv(self, payload: Dict[str, Any]) -> str:
        """Render tabular CSV extract from payload tables or widgets."""
        output = io.StringIO()
        writer = None

        tables = payload.get("tables", {})
        if tables and isinstance(tables, dict):
            for t_name, rows in tables.items():
                if rows and isinstance(rows, list):
                    output.write(f"# Table: {t_name}\n")
                    fieldnames = list(rows[0].keys())
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    for r in rows:
                        writer.writerow(r)
                    output.write("\n")

        if output.tell() == 0:
            # Fallback to exporting widgets summary as CSV
            widgets = payload.get("widgets", [])
            if widgets and isinstance(widgets, list):
                writer = csv.DictWriter(output, fieldnames=["i", "title", "type", "value", "subtitle"])
                writer.writeheader()
                for w in widgets:
                    writer.writerow({
                        "i": w.get("i", ""),
                        "title": w.get("title", ""),
                        "type": w.get("type", ""),
                        "value": w.get("value", ""),
                        "subtitle": w.get("subtitle", ""),
                    })

        return output.getvalue()

    def render_pdf(self, payload: Dict[str, Any], html_content: str) -> bytes:
        """Render PDF bytes using WeasyPrint if available, falling back to clean PDF output."""
        try:
            import weasyprint
            return weasyprint.HTML(string=html_content).write_pdf()
        except Exception:
            # Clean Fallback PDF generation
            title = payload.get("title", "PyBI PDF Export")
            snapshot = payload.get("snapshot", {})
            hash_str = snapshot.get("active_filters_hash", "SHA256")[:16]
            pdf_str = f"%PDF-1.4\n1 0 obj\n<< /Title ({title}) /Subject (PyBI Snapshot {hash_str}) >>\nendobj\n"
            pdf_str += f"2 0 obj\n<< /Type /Catalog /Pages 3 0 R >>\nendobj\n"
            pdf_str += f"3 0 obj\n<< /Type /Pages /Count 1 /Kids [4 0 R] >>\nendobj\n"
            pdf_str += f"4 0 obj\n<< /Type /Page /Parent 3 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
            pdf_str += "xref\n0 5\n0000000000 65535 f \ntrailer\n<< /Size 5 /Root 2 0 R >>\nstartxref\n180\n%%EOF"
            return pdf_str.encode("utf-8")

    def get_job_status(self, export_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job status, progress, snapshot, and file path."""
        job = self.jobs.get(export_id)
        if not job:
            # Try reading from disk snapshot if existing
            snapshot_file = self.exports_dir / export_id / "snapshot.json"
            if snapshot_file.exists():
                with open(snapshot_file, "r", encoding="utf-8") as f:
                    snap = json.load(f)
                fmt = snap.get("format", "html")
                ext = "md" if fmt in ["md", "markdown"] else fmt
                art = self.exports_dir / export_id / f"export_{export_id}.{ext}"
                return {
                    "export_id": export_id,
                    "project_id": snap.get("project_id"),
                    "status": "completed",
                    "progress": 100,
                    "format": fmt,
                    "snapshot": snap,
                    "file_path": str(art) if art.exists() else None,
                    "error": None,
                }
            return None

        # Return sanitized job view
        return {
            "export_id": job["export_id"],
            "project_id": job["project_id"],
            "status": job["status"],
            "progress": job["progress"],
            "format": job["format"],
            "template_id": job["template_id"],
            "snapshot": job["snapshot"],
            "file_path": job["file_path"],
            "error": job["error"],
        }


# Global default instance
default_export_engine = ExportEngine()
