"""Registry mapping ETL node type strings to concrete ETLNode classes."""

from typing import Dict, Type
from pybi.core.interfaces import ETLNode
from .source import DataSourceNode
from .transform import FilterNode, SelectNode, GroupByNode, JoinNode, PivotNode
from .output import OutputNode

NODE_REGISTRY: Dict[str, Type[ETLNode]] = {
    "DataSource": DataSourceNode,
    "Filter": FilterNode,
    "Select": SelectNode,
    "GroupBy": GroupByNode,
    "Join": JoinNode,
    "Pivot": PivotNode,
    "Output": OutputNode,
}

_TRANSFORM_NODES: Dict[str, Type[ETLNode]] = {
    "filter": FilterNode,
    "select": SelectNode,
    "groupby": GroupByNode,
    "group_by": GroupByNode,
    "join": JoinNode,
    "pivot": PivotNode,
}


def get_node_class(node_type: str, transform_type: str | None = None) -> Type[ETLNode]:
    """Return the concrete ETLNode class for a given node_type or transform_type."""
    if transform_type and transform_type.lower() in _TRANSFORM_NODES:
        return _TRANSFORM_NODES[transform_type.lower()]
    return NODE_REGISTRY.get(node_type, DataSourceNode)
