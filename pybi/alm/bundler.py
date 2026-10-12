"""Application Lifecycle Management (ALM) project bundler for PyBI (.pybi format)."""

import json
import os
import shutil
import zipfile
from pathlib import Path

from pybi.core.storage import FileProjectStorage, default_storage, sanitize_project_id


class ProjectBundler:
    """Creates and extracts portable .pybi ZIP project archives."""

    @staticmethod
    def create_bundle(
        project_id: str,
        output_path: str | Path | None = None,
        storage: FileProjectStorage | None = None,
    ) -> Path:
        """Export a project and all associated assets into a portable .pybi ZIP file.

        Args:
            project_id: Source project ID.
            output_path: Target .pybi file output path.
            storage: Storage backend instance.

        Returns:
            Path: Path to created .pybi bundle file.
        """
        st = storage or default_storage
        safe_id = sanitize_project_id(project_id)
        if not st.project_exists(safe_id):
            raise FileNotFoundError(f"Project '{project_id}' not found.")

        out_file = Path(output_path) if output_path else Path(f"{safe_id}.pybi")
        out_file.parent.mkdir(parents=True, exist_ok=True)

        proj_json_path = st._get_project_path(safe_id)
        proj_dir = Path(st.projects_dir) / safe_id

        with zipfile.ZipFile(out_file, "w", zipfile.ZIP_DEFLATED) as zipf:
            # 1. Root project.json
            zipf.write(proj_json_path, arcname="project.json")

            # 2. Add files inside project directory (data/, semantic_model.yaml, etc.)
            if proj_dir.exists():
                for root, _, files in os.walk(proj_dir):
                    for file in files:
                        full_path = Path(root) / file
                        rel_path = full_path.relative_to(proj_dir)
                        zipf.write(full_path, arcname=str(rel_path))

        return out_file.resolve()

    @staticmethod
    def extract_bundle(
        bundle_path: str | Path,
        target_project_id: str | None = None,
        storage: FileProjectStorage | None = None,
    ) -> str:
        """Import a .pybi bundle archive, restoring project state and assets.

        Args:
            bundle_path: Path to .pybi bundle archive.
            target_project_id: Optional override for restored project ID.
            storage: Storage backend instance.

        Returns:
            str: Imported project ID.
        """
        st = storage or default_storage
        b_path = Path(bundle_path)
        if not b_path.exists():
            raise FileNotFoundError(f"Bundle file '{bundle_path}' not found.")

        temp_dir = b_path.parent / f"_extract_tmp_{b_path.stem}"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(b_path, "r") as zipf:
                zipf.extractall(temp_dir)

            proj_json_path = temp_dir / "project.json"
            if not proj_json_path.exists():
                raise ValueError("Invalid .pybi archive: missing root 'project.json'.")

            with open(proj_json_path, "r", encoding="utf-8") as f:
                proj_data = json.load(f)

            pid = sanitize_project_id(target_project_id or proj_data.get("project_id") or b_path.stem)
            proj_data["project_id"] = pid

            # Write restored project.json to storage
            target_json = st._get_project_path(pid)
            os.makedirs(os.path.dirname(target_json), exist_ok=True)
            with open(target_json, "w", encoding="utf-8") as f:
                json.dump(proj_data, f, indent=2)

            # Copy remaining extracted contents to project directory
            target_proj_dir = Path(st.projects_dir) / pid
            os.makedirs(target_proj_dir, exist_ok=True)

            for item in temp_dir.iterdir():
                if item.name == "project.json":
                    continue
                dest = target_proj_dir / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

            return pid
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
