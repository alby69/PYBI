"""Autodetect relationship logic for Semantic Model View."""

from typing import List, Optional, Set, Tuple
from pybi.models.semantic import (
    CardinalityType,
    CrossFilterDirection,
    JoinType,
    Relationship,
    TableMetadata,
)


def autodetect_model_relationships(
    tables: List[TableMetadata],
    existing_relationships: Optional[List[Relationship]] = None,
) -> List[Relationship]:
    """Scans tables for matching column names and data types to propose relationships.

    Args:
        tables: List of TableMetadata objects to scan.
        existing_relationships: Existing relationships to avoid duplicating.

    Returns:
        List[Relationship]: List of newly detected relationships.
    """
    detected: List[Relationship] = []
    existing_pairs: Set[Tuple[str, str, str, str]] = set()

    if existing_relationships:
        for r in existing_relationships:
            existing_pairs.add((r.from_table, r.from_column, r.to_table, r.to_column))
            existing_pairs.add((r.to_table, r.to_column, r.from_table, r.from_column))

    for i in range(len(tables)):
        for j in range(i + 1, len(tables)):
            tbl1 = tables[i]
            tbl2 = tables[j]
            for c1 in tbl1.columns:
                for c2 in tbl2.columns:
                    # Match by column name (case-insensitive) and compatible data type
                    c1_name = c1.name.lower()
                    c2_name = c2.name.lower()
                    c1_type = c1.data_type.lower()
                    c2_type = c2.data_type.lower()

                    if c1_name == c2_name and (c1_type == c2_type or {c1_type, c2_type}.issubset({"number", "integer", "float", "int"})):
                        pair1 = (tbl1.name, c1.name, tbl2.name, c2.name)
                        pair2 = (tbl2.name, c2.name, tbl1.name, c1.name)
                        if pair1 in existing_pairs or pair2 in existing_pairs:
                            continue

                        if c2.is_key and not c1.is_key:
                            from_t, from_c = tbl1.name, c1.name
                            to_t, to_c = tbl2.name, c2.name
                            card = CardinalityType.MANY_TO_ONE
                        elif c1.is_key and not c2.is_key:
                            from_t, from_c = tbl2.name, c2.name
                            to_t, to_c = tbl1.name, c1.name
                            card = CardinalityType.MANY_TO_ONE
                        elif c1.is_key and c2.is_key:
                            from_t, from_c = tbl1.name, c1.name
                            to_t, to_c = tbl2.name, c2.name
                            card = CardinalityType.ONE_TO_ONE
                        else:
                            from_t, from_c = tbl1.name, c1.name
                            to_t, to_c = tbl2.name, c2.name
                            card = CardinalityType.MANY_TO_ONE

                        rel_id = f"rel_{from_t}_{from_c}_{to_t}_{to_c}".lower()
                        rel = Relationship(
                            id=rel_id,
                            from_table=from_t,
                            from_column=from_c,
                            to_table=to_t,
                            to_column=to_c,
                            cardinality=card,
                            cross_filter_direction=CrossFilterDirection.SINGLE,
                            join_type=JoinType.LEFT,
                            is_active=True,
                            description=f"Auto-detected relationship between {from_t}.{from_c} and {to_t}.{to_c}",
                        )
                        detected.append(rel)
                        existing_pairs.add(pair1)
                        existing_pairs.add(pair2)

    return detected
