"""Application Lifecycle Management (ALM) Project Bundler for .pybi packages."""

import io
import json
import logging
import os
from pathlib import Path

from typing import Any, Dict, Optional, Union
import zipfile

from pybi.core.storage import default_storage

log = logging.getLogger(__name__)


class ProjectBundler:
    """Export and import complete PyBI project bundles as .pybi (ZIP) archives."""

    @staticmethod
    def export_bundle(project_id: str) -> bytes:
        """Export project metadata, layouts, ETL queries, and data files into .pybi ZIP bytes."""
        buffer = io.BytesIO()
        p_dir = default_storage.get_project_data_dir(project_id)
        project_dir = Path(p_dir) if isinstance(p_dir, (str, Path)) else Path(default_storage.base_dir) / "projects" / project_id

        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            if project_dir.exists():
                for root, _, files in os.walk(project_dir):
                    for file in files:
                        full_path = Path(root) / file
                        arcname = full_path.relative_to(project_dir)
                        zf.write(full_path, arcname=arcname)
            else:
                # Minimal fallback project manifest
                manifest = {
                    "project_id": project_id,
                    "name": project_id,
                    "version": "1.0.0",
                }
                zf.writestr("project.json", json.dumps(manifest, indent=2))

        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def import_bundle(bundle_bytes: bytes, target_project_id: Optional[str] = None) -> Dict[str, Any]:
        """Import a .pybi ZIP archive as a new or existing project."""
        buffer = io.BytesIO(bundle_bytes)
        with zipfile.ZipFile(buffer, "r") as zf:
            manifest_str = None
            if "project.json" in zf.namelist():
                manifest_str = zf.read("project.json").decode("utf-8")

            manifest = json.loads(manifest_str) if manifest_str else {}
            pid = target_project_id or manifest.get("project_id") or "imported_project"

            base_dir = getattr(default_storage, "base_dir", Path("pybi_data"))
            target_dir = Path(base_dir) / "projects" / pid
            target_dir.mkdir(parents=True, exist_ok=True)

            zf.extractall(target_dir)

            return {
                "project_id": pid,
                "status": "success",
                "extracted_files": zf.namelist(),
            }
