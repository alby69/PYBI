"""Snapshot module for generating immutable metadata and SHA-256 filter hashes."""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional
import uuid


def hash_filter_context(filter_context: Optional[Any]) -> str:
    """Compute deterministic SHA-256 hash of active filter context state."""
    if not filter_context:
        return hashlib.sha256(b"{}").hexdigest()

    serialized_filters: List[Dict[str, Any]] = []

    if hasattr(filter_context, "filters"):
        raw_filters = getattr(filter_context, "filters", {})
        if isinstance(raw_filters, dict):
            for key in sorted(raw_filters.keys()):
                f = raw_filters[key]
                if hasattr(f, "table") and hasattr(f, "column"):
                    serialized_filters.append({
                        "key": key,
                        "table": f.table,
                        "column": f.column,
                        "values": sorted(f.values) if isinstance(f.values, list) else f.values,
                        "operator": getattr(f, "operator", "IN"),
                    })
                elif isinstance(f, dict):
                    serialized_filters.append({
                        "key": key,
                        "table": f.get("table", ""),
                        "column": f.get("column", ""),
                        "values": sorted(f.get("values", [])) if isinstance(f.get("values"), list) else f.get("values"),
                        "operator": f.get("operator", "IN"),
                    })
    elif isinstance(filter_context, dict):
        for key in sorted(filter_context.keys()):
            val = filter_context[key]
            serialized_filters.append({
                "key": key,
                "value": sorted(val) if isinstance(val, list) else str(val)
            })
    elif isinstance(filter_context, list):
        for item in filter_context:
            if isinstance(item, dict):
                serialized_filters.append(dict(sorted(item.items())))
            else:
                serialized_filters.append({"rule": str(item)})

    json_bytes = json.dumps(serialized_filters, sort_keys=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()


def create_snapshot(
    project_id: str,
    project_version: str = "1.0.0",
    filter_context: Optional[Any] = None,
    source_files: Optional[List[str]] = None,
    export_format: str = "html",
    template_id: Optional[str] = None,
    ai_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate snapshot metadata dictionary freezing project state during export."""
    export_id = f"exp_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    filter_hash = hash_filter_context(filter_context)

    active_filters_repr: Dict[str, Any] = {}
    if hasattr(filter_context, "filters") and isinstance(filter_context.filters, dict):
        for k, v in filter_context.filters.items():
            if hasattr(v, "table") and hasattr(v, "column"):
                active_filters_repr[k] = {
                    "table": v.table,
                    "column": v.column,
                    "values": v.values,
                    "operator": getattr(v, "operator", "IN"),
                }
            elif isinstance(v, dict):
                active_filters_repr[k] = v
    elif isinstance(filter_context, dict):
        active_filters_repr = filter_context

    return {
        "export_id": export_id,
        "timestamp": now_iso,
        "project_id": project_id,
        "project_version": project_version,
        "active_filters_hash": filter_hash,
        "active_filters": active_filters_repr,
        "source_files_list": source_files or [],
        "format": export_format.lower(),
        "template_id": template_id or ("report_dati.html" if export_format.lower() == "html" else "documento_knowledge.md"),
        "ai_compilation_prompt": ai_prompt or None,
    }
