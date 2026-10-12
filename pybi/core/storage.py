"""Project serialization and filesystem storage module for PyBI."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
import os
import shutil
from typing import Any, Dict, List, Optional, Union


DEFAULT_STORAGE_DIR = "pybi_data"
ID_SAFE_CHARS = ("-", "_")
DEFAULT_DASHBOARD_ID = "dash_1"
DEFAULT_DASHBOARD_NAME = "Dashboard 1"


def sanitize_project_id(project_id: str) -> str:
    """Normalize a project id into a filesystem-safe name.

    Args:
        project_id: Raw project identifier typed by the user.

    Returns:
        str: Sanitized identifier, or "default" when nothing usable remains.
    """
    safe_id = "".join(c for c in project_id if c.isalnum() or c in ID_SAFE_CHARS).strip()
    return safe_id or "default"


def resolve_storage_dir(storage_dir: Optional[str] = None) -> str:
    """Resolve the directory holding project JSON files.

    Resolution order: explicit argument, DATA_DIR environment variable, "pybi_data".

    Args:
        storage_dir: Optional explicit directory overriding environment lookup.

    Returns:
        str: Directory path to use for project storage.
    """
    if storage_dir:
        return storage_dir
    return os.environ.get("DATA_DIR") or DEFAULT_STORAGE_DIR


class ProjectStorage(ABC):
    """Abstract base class defining the interface for PyBI project storage backends."""

    @abstractmethod
    def list_dashboards(self, project_id: str) -> List[Dict[str, Any]]:
        """List the dashboards saved for a project."""
        pass

    @abstractmethod
    def load_dashboard(self, project_id: str, dashboard_id: str) -> Any:
        """Load a named dashboard's layout for a project."""
        pass

    @abstractmethod
    def save_dashboard(self, project_id: str, dashboard_id: str, name: str, layout: Any) -> None:
        """Create or update a named dashboard for a project."""
        pass

    @abstractmethod
    def get_project_data_dir(self, project_id: str) -> str:
        """Returns and creates (if it does not exist) the 'data' directory for the project.

        Args:
            project_id: Identifier of the project.

        Returns:
            str: Path to the project's data directory.
        """
        pass

    @abstractmethod
    def save_project(
        self,
        project_id: str,
        etl_dag: Optional[Dict[str, Any]] = None,
        dashboard_layout: Optional[Any] = None,
        name: str = "",
        dashboards: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Save project configuration."""
        pass

    @abstractmethod
    def load_project(self, project_id: str) -> Dict[str, Any]:
        """Load project configuration by project_id."""
        pass

    @abstractmethod
    def list_projects(self) -> List[str]:
        """List all saved project IDs."""
        pass

    @abstractmethod
    def delete_project(self, project_id: str) -> bool:
        """Delete project configuration by project_id."""
        pass

    @abstractmethod
    def project_exists(self, project_id: str) -> bool:
        """Check whether a project has already been saved."""
        pass


class FileProjectStorage(ProjectStorage):
    """JSON file system storage implementation for PyBI projects under pybi_data/."""

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        """Initialize FileProjectStorage.

        Args:
            storage_dir: Base directory path to store project files. Defaults to
                the DATA_DIR environment variable, then "pybi_data".
        """
        self.storage_dir = resolve_storage_dir(storage_dir)
        self.projects_dir = os.path.join(self.storage_dir, "projects")
        os.makedirs(self.projects_dir, exist_ok=True)

    def _get_project_path(self, project_id: str) -> str:
        """Get filesystem path for a project JSON file.

        Args:
            project_id: Identifier of the project.

        Returns:
            str: Full path to the project JSON file.
        """
        return os.path.join(self.projects_dir, f"{sanitize_project_id(project_id)}.json")

    def _make_dashboard(self, dashboard_id: str, name: str, layout: Any, now_str: str) -> Dict[str, Any]:
        """Build a dashboard entry for the project's dashboards list."""
        return {
            "id": dashboard_id,
            "name": name or dashboard_id,
            "layout": layout,
            "created_at": now_str,
            "updated_at": now_str,
        }

    def _project_dashboards(self, project_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return the dashboards list of a project, migrating the legacy single layout.

        Legacy projects only store ``dashboard_layout``; they are treated as a single
        dashboard named "Dashboard 1".
        """
        dashboards = project_data.get("dashboards")
        if dashboards is not None:
            return dashboards
        layout = project_data.get("dashboard_layout")
        if layout is not None:
            now_str = project_data.get("updated_at") or datetime.now(timezone.utc).isoformat()
            return [self._make_dashboard(DEFAULT_DASHBOARD_ID, DEFAULT_DASHBOARD_NAME, layout, now_str)]
        return []

    def get_project_data_dir(self, project_id: str) -> str:
        """Returns and creates (if it does not exist) the 'data' directory for the project.

        Args:
            project_id: Identifier of the project.

        Returns:
            str: Path to the project's data directory.
        """
        safe_id = sanitize_project_id(project_id)
        data_dir = os.path.join(self.projects_dir, safe_id, "data")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    def get_project_cache_dir(self, project_id: str) -> str:
        """Returns and creates (if it does not exist) the 'cache' directory for the project."""
        safe_id = sanitize_project_id(project_id)
        cache_dir = os.path.join(self.storage_dir, "cache", safe_id)
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    def get_cached_table(self, project_id: str, cache_key: str) -> Optional[Any]:
        """Load cached Parquet file if exists."""
        import polars as pl
        cache_dir = self.get_project_cache_dir(project_id)
        file_path = os.path.join(cache_dir, f"{cache_key}.parquet")
        if os.path.exists(file_path):
            try:
                return pl.read_parquet(file_path)
            except Exception:
                return None
        return None

    def save_cached_table(self, project_id: str, cache_key: str, df: Any) -> str:
        """Save DataFrame as Parquet in the project's cache directory."""
        import polars as pl
        cache_dir = self.get_project_cache_dir(project_id)
        file_path = os.path.join(cache_dir, f"{cache_key}.parquet")
        if isinstance(df, pl.DataFrame):
            df.write_parquet(file_path)
        return file_path

    def save_project(
        self,
        project_id: str,
        etl_dag: Optional[Dict[str, Any]] = None,
        dashboard_layout: Optional[Any] = None,
        name: str = "",
        dashboards: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Save project configuration to filesystem JSON file.

        Args:
            project_id: Identifier for the project.
            etl_dag: Optional ETL DAG dictionary (nodes and edges).
            dashboard_layout: Optional legacy dashboard layout list or dictionary
                (treated as the primary dashboard).
            name: Optional human-readable project name.
            dashboards: Optional full dashboards list; when provided it wins over
                ``dashboard_layout``. When omitted, existing dashboards are preserved.

        Returns:
            Dict[str, Any]: Saved project dictionary.
        """
        self.get_project_data_dir(project_id)
        filepath = self._get_project_path(project_id)
        existing_data = {}
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except Exception:
                existing_data = {}

        now_str = datetime.now(timezone.utc).isoformat()

        if dashboards is not None:
            if dashboard_layout is not None:
                # Legacy param still overrides the primary (first) dashboard layout.
                if dashboards:
                    dashboards = list(dashboards)
                    dashboards[0]["layout"] = dashboard_layout
                else:
                    dashboards = [self._make_dashboard(DEFAULT_DASHBOARD_ID, DEFAULT_DASHBOARD_NAME, dashboard_layout, now_str)]
        elif dashboard_layout is not None:
            dashboards = [self._make_dashboard(DEFAULT_DASHBOARD_ID, DEFAULT_DASHBOARD_NAME, dashboard_layout, now_str)]
        elif "dashboards" in existing_data:
            dashboards = existing_data["dashboards"]
        elif existing_data.get("dashboard_layout") is not None:
            dashboards = self._project_dashboards(existing_data)
        else:
            dashboards = []

        project_data = {
            "project_id": project_id,
            "name": name or existing_data.get("name") or project_id,
            "etl_dag": etl_dag if etl_dag is not None else existing_data.get("etl_dag", {"nodes": [], "edges": []}),
            "dashboards": dashboards,
            "dashboard_layout": dashboards[0].get("layout") if dashboards else (dashboard_layout if dashboard_layout is not None else existing_data.get("dashboard_layout")),
            "created_at": existing_data.get("created_at", now_str),
            "updated_at": now_str,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=2)

        return project_data

    def load_project(self, project_id: str) -> Dict[str, Any]:
        """Load project configuration from filesystem JSON file.

        Args:
            project_id: Identifier for the project.

        Returns:
            Dict[str, Any]: Loaded project dictionary.
        """
        filepath = self._get_project_path(project_id)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Project '{project_id}' not found at '{filepath}'")

        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_projects(self) -> List[str]:
        """List all project IDs stored in the filesystem directory.

        Returns:
            List[str]: List of project IDs.
        """
        if not os.path.exists(self.projects_dir):
            return []
        projects = []
        for filename in os.listdir(self.projects_dir):
            if filename.endswith(".json"):
                projects.append(filename[:-5])
        return sorted(projects)

    def save_uploaded_file(self, project_id: str, filename: str, content: bytes) -> str:
        """Save an uploaded file in the project's data directory.

        Args:
            project_id: Identifier of the project.
            filename: Original name of the uploaded file.
            content: Raw bytes content of the file.

        Returns:
            str: Absolute path to the saved file.
        """
        safe_filename = os.path.basename(filename)
        data_dir = self.get_project_data_dir(project_id)
        file_path = os.path.join(data_dir, safe_filename)

        with open(file_path, "wb") as f:
            f.write(content)

        return os.path.abspath(file_path)

    def list_project_files(self, project_id: str) -> List[str]:
        """Return list of files in the project's data directory.

        Args:
            project_id: Identifier of the project.

        Returns:
            List[str]: Filenames of files present in project's data directory.
        """
        data_dir = self.get_project_data_dir(project_id)
        if not os.path.exists(data_dir):
            return []
        return [f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]

    def delete_project_file(self, project_id: str, filename: str) -> bool:
        """Delete a specific file from the project's data directory.

        Args:
            project_id: Identifier of the project.
            filename: Name of the file to delete.

        Returns:
            bool: True if deleted, False if file did not exist.
        """
        safe_id = sanitize_project_id(project_id)
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(self.projects_dir, safe_id, "data", safe_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    def delete_project(self, project_id: str) -> bool:
        """Delete project configuration JSON file and its associated directory structure.

        Args:
            project_id: Identifier of the project.

        Returns:
            bool: True if deleted, False if file did not exist.
        """
        filepath = self._get_project_path(project_id)
        deleted_file = False
        if os.path.exists(filepath):
            os.remove(filepath)
            deleted_file = True

        safe_id = sanitize_project_id(project_id)
        project_dir = os.path.join(self.projects_dir, safe_id)
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)

        return deleted_file

    def project_exists(self, project_id: str) -> bool:
        """Check whether a project has already been saved.

        Args:
            project_id: Identifier of the project.

        Returns:
            bool: True if the project file exists.
        """
        return os.path.exists(self._get_project_path(project_id))

    def rename_project(self, project_id: str, new_project_id: str, name: Optional[str] = None) -> str:
        """Rename a project, preserving its ETL DAG and dashboard layout.

        Args:
            project_id: Current identifier of the project.
            new_project_id: New identifier for the project.
            name: Optional new human-readable name, kept as-is when omitted.

        Returns:
            str: The sanitized new identifier actually used on disk.

        Raises:
            FileNotFoundError: If the source project does not exist.
            ValueError: If the sanitized target id is already taken by another project.
        """
        source = self.load_project(project_id)
        target_id = sanitize_project_id(new_project_id)
        if target_id == sanitize_project_id(project_id):
            self.save_project(target_id, name=name if name is not None else source.get("name", ""))
            return target_id
        if self.project_exists(target_id):
            raise ValueError(f"Project '{target_id}' already exists.")

        self.save_project(
            project_id=target_id,
            etl_dag=source.get("etl_dag", {"nodes": [], "edges": []}),
            dashboards=source.get("dashboards") or self._project_dashboards(source),
            name=name if name is not None else source.get("name", ""),
        )
        self.delete_project(project_id)
        return target_id

    def save_etl_dag(self, project_id: str, etl_dag: Dict[str, Any]) -> None:
        """Convenience method to save only the ETL DAG for a project."""
        self.save_project(project_id=project_id, etl_dag=etl_dag)

    def load_etl_dag(self, project_id: str) -> Dict[str, Any]:
        """Convenience method to load only the ETL DAG for a project."""
        proj = self.load_project(project_id)
        return proj.get("etl_dag", {"nodes": [], "edges": []})

    def list_dashboards(self, project_id: str) -> List[Dict[str, Any]]:
        """List the dashboards saved for a project.

        Returns:
            List[Dict[str, Any]]: A list of ``{"id", "name"}`` summaries, or an
            empty list when the project has no saved dashboards.
        """
        if not self.project_exists(project_id):
            return []
        proj = self.load_project(project_id)
        return [{"id": d["id"], "name": d.get("name") or d["id"]} for d in self._project_dashboards(proj)]

    def load_dashboard(self, project_id: str, dashboard_id: str) -> Any:
        """Load the layout of a named dashboard for a project.

        Returns:
            The dashboard layout list (possibly empty), or None when either the
            project or the dashboard does not exist.
        """
        if not self.project_exists(project_id):
            return None
        proj = self.load_project(project_id)
        for dashboard in self._project_dashboards(proj):
            if dashboard["id"] == dashboard_id:
                return dashboard.get("layout")
        return None

    def save_dashboard(self, project_id: str, dashboard_id: str, name: str, layout: Any) -> None:
        """Create or update a named dashboard for a project.

        The ETL DAG and other dashboards are preserved.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        if self.project_exists(project_id):
            proj = self.load_project(project_id)
        else:
            proj = {"project_id": project_id}

        dashboards = {d["id"]: dict(d) for d in self._project_dashboards(proj)}
        entry = dashboards.get(dashboard_id)
        if entry is None:
            dashboards[dashboard_id] = self._make_dashboard(dashboard_id, name, layout, now_str)
        else:
            entry["name"] = name or entry.get("name") or dashboard_id
            entry["layout"] = layout
            entry["updated_at"] = now_str

        self.save_project(
            project_id=project_id,
            etl_dag=proj.get("etl_dag"),
            name=proj.get("name", ""),
            dashboards=list(dashboards.values()),
        )

    def delete_dashboard(self, project_id: str, dashboard_id: str) -> bool:
        """Delete a named dashboard from a project.

        Returns:
            bool: True when the dashboard was removed, False when it did not exist.
        """
        if not self.project_exists(project_id):
            return False
        proj = self.load_project(project_id)
        dashboards = [d for d in self._project_dashboards(proj) if d["id"] != dashboard_id]
        if len(dashboards) == len(self._project_dashboards(proj)):
            return False
        self.save_project(
            project_id=project_id,
            etl_dag=proj.get("etl_dag"),
            name=proj.get("name", ""),
            dashboards=dashboards,
        )
        return True

    def save_dashboard_layout(self, project_id: str, layout: Any) -> None:
        """Convenience method to save only the primary Dashboard Layout for a project."""
        self.save_dashboard(project_id, DEFAULT_DASHBOARD_ID, DEFAULT_DASHBOARD_NAME, layout)

    def load_dashboard_layout(self, project_id: str) -> Any:
        """Load the saved Dashboard Layout for a project.

        Returns:
            The saved layout list (possibly empty when the user intentionally
            saved an empty dashboard), or None when no layout was ever saved.
        """
        proj = self.load_project(project_id)
        dashboards = self._project_dashboards(proj)
        if not dashboards:
            return None
        layout = dashboards[0].get("layout")
        return None if layout is None else layout


# Default singleton instance for general application storage
default_storage = FileProjectStorage()
