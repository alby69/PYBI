"""Registry mapping ETL node type strings to concrete ETLNode classes."""

from typing import Dict, Type
from pybi.core.interfaces import ETLNode
from .source import DataSourceNode
from .transform import (
    CalculatedColumnNode,
    CastColumnNode,
    ConditionalColumnNode,
    DeduplicateNode,
    FillDownNode,
    FilterNode,
    GroupByNode,
    IndexColumnNode,
    JoinNode,
    PivotNode,
    RenameColumnNode,
    SelectNode,
    SplitColumnNode,
    TextTransformNode,
    UnpivotNode,
)
from .output import OutputNode

NODE_REGISTRY: Dict[str, Type[ETLNode]] = {
    "DataSource": DataSourceNode,
    "Filter": FilterNode,
    "Select": SelectNode,
    "GroupBy": GroupByNode,
    "Join": JoinNode,
    "Pivot": PivotNode,
    "Unpivot": UnpivotNode,
    "FillDown": FillDownNode,
    "RenameColumn": RenameColumnNode,
    "CastColumn": CastColumnNode,
    "SplitColumn": SplitColumnNode,
    "TextTransform": TextTransformNode,
    "Deduplicate": DeduplicateNode,
    "ConditionalColumn": ConditionalColumnNode,
    "IndexColumn": IndexColumnNode,
    "AddColumn": CalculatedColumnNode,
    "Output": OutputNode,
}

_TRANSFORM_NODES: Dict[str, Type[ETLNode]] = {
    "filter": FilterNode,
    "select": SelectNode,
    "groupby": GroupByNode,
    "group_by": GroupByNode,
    "join": JoinNode,
    "pivot": PivotNode,
    "unpivot": UnpivotNode,
    "fill_down": FillDownNode,
    "filldown": FillDownNode,
    "rename_column": RenameColumnNode,
    "rename": RenameColumnNode,
    "cast_column": CastColumnNode,
    "cast": CastColumnNode,
    "split_column": SplitColumnNode,
    "split": SplitColumnNode,
    "text_transform": TextTransformNode,
    "text": TextTransformNode,
    "deduplicate": DeduplicateNode,
    "distinct": DeduplicateNode,
    "conditional_column": ConditionalColumnNode,
    "conditional": ConditionalColumnNode,
    "index_column": IndexColumnNode,
    "index": IndexColumnNode,
    "add_column": CalculatedColumnNode,
    "addcolumn": CalculatedColumnNode,
    "calculated_column": CalculatedColumnNode,
}


def get_node_class(node_type: str, transform_type: str | None = None) -> Type[ETLNode]:
    """Return the concrete ETLNode class for a given node_type or transform_type."""
    if transform_type and transform_type.lower() in _TRANSFORM_NODES:
        return _TRANSFORM_NODES[transform_type.lower()]
    return NODE_REGISTRY.get(node_type, DataSourceNode)
