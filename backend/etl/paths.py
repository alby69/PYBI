"""Shared path helpers for ETL data sources."""

import os
from typing import Optional


def resolve_data_path(filepath: str, base_dir: Optional[str] = None) -> str:
    """Resolve a data file path against the project data folder.

    Absolute paths that exist are returned untouched. Relative paths are
    looked up inside ``base_dir`` first, then by basename, so a DAG saved with
    an absolute path still works when the project folder has been moved.
    """
    if not filepath or not base_dir:
        return filepath
    if os.path.isabs(filepath) and os.path.exists(filepath):
        return filepath
    candidates = []
    if not os.path.isabs(filepath):
        candidates.append(os.path.join(base_dir, filepath))
    candidates.append(os.path.join(base_dir, os.path.basename(filepath)))
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return filepath
