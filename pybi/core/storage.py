"""Project serialization and filesystem storage module for PyBI."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
import os
from typing import Any, Dict, List, Optional, Union


class ProjectStorage(ABC):
    """Abstract base class defining the interface for PyBI project storage backends."""

    @abstractmethod
    def save_project(
        self,
        project_id: str,
        etl_dag: Optional[Dict[str, Any]] = None,
        dashboard_layout: Optional[Any] = None,
        name: str = "",
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


class FileProjectStorage(ProjectStorage):
    """JSON file system storage implementation for PyBI projects under pybi_data/."""

    def __init__(self, storage_dir: str = "pybi_data") -> None:
        """Initialize FileProjectStorage.

        Args:
            storage_dir: Base directory path to store project files.
        """
        self.storage_dir = storage_dir
        self.projects_dir = os.path.join(self.storage_dir, "projects")
        os.makedirs(self.projects_dir, exist_ok=True)

    def _get_project_path(self, project_id: str) -> str:
        """Get filesystem path for a project JSON file.

        Args:
            project_id: Identifier of the project.

        Returns:
            str: Full path to the project JSON file.
        """
        safe_id = "".join(c for c in project_id if c.isalnum() or c in ("-", "_")).strip()
        if not safe_id:
            safe_id = "default"
        return os.path.join(self.projects_dir, f"{safe_id}.json")

    def save_project(
        self,
        project_id: str,
        etl_dag: Optional[Dict[str, Any]] = None,
        dashboard_layout: Optional[Any] = None,
        name: str = "",
    ) -> Dict[str, Any]:
        """Save project configuration to filesystem JSON file.

        Args:
            project_id: Identifier for the project.
            etl_dag: Optional ETL DAG dictionary (nodes and edges).
            dashboard_layout: Optional dashboard layout list or dictionary.
            name: Optional human-readable project name.

        Returns:
            Dict[str, Any]: Saved project dictionary.
        """
        filepath = self._get_project_path(project_id)
        existing_data = {}
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except Exception:
                existing_data = {}

        now_str = datetime.now(timezone.utc).isoformat()

        project_data = {
            "project_id": project_id,
            "name": name or existing_data.get("name") or project_id,
            "etl_dag": etl_dag if etl_dag is not None else existing_data.get("etl_dag", {"nodes": [], "edges": []}),
            "dashboard_layout": dashboard_layout if dashboard_layout is not None else existing_data.get("dashboard_layout", []),
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

    def delete_project(self, project_id: str) -> bool:
        """Delete project configuration JSON file.

        Args:
            project_id: Identifier for the project.

        Returns:
            bool: True if deleted, False if file did not exist.
        """
        filepath = self._get_project_path(project_id)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

    def save_etl_dag(self, project_id: str, etl_dag: Dict[str, Any]) -> None:
        """Convenience method to save only the ETL DAG for a project."""
        self.save_project(project_id=project_id, etl_dag=etl_dag)

    def load_etl_dag(self, project_id: str) -> Dict[str, Any]:
        """Convenience method to load only the ETL DAG for a project."""
        proj = self.load_project(project_id)
        return proj.get("etl_dag", {"nodes": [], "edges": []})

    def save_dashboard_layout(self, project_id: str, layout: Any) -> None:
        """Convenience method to save only the Dashboard Layout for a project."""
        self.save_project(project_id=project_id, dashboard_layout=layout)

    def load_dashboard_layout(self, project_id: str) -> Any:
        """Convenience method to load only the Dashboard Layout for a project."""
        proj = self.load_project(project_id)
        return proj.get("dashboard_layout", [])


# Default singleton instance for general application storage
default_storage = FileProjectStorage()
