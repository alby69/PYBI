"""QueryBuilder translating visual configurations into DuckDB SQL queries."""

from typing import Any, Dict, Optional
from pybi.dashboard.filter_context import FilterContext
from pybi.report.visuals import BarChartVisual, BaseVisual, KPIVisual, LineChartVisual, TableVisual


class QueryBuilder:
    """Translates visual specifications and field assignments into SQL queries."""

    @staticmethod
    def build_query(visual_type: str, visual_id: str, table_name: str, config: Dict[str, Any], filter_context: Optional[FilterContext] = None) -> str:
        """Construct SQL query string for a visual type.

        Args:
            visual_type: Type of visual ('bar', 'line', 'table', 'kpi').
            visual_id: Unique visual id.
            table_name: Target semantic table name.
            config: Visual field assignment mapping.
            filter_context: Optional FilterContext containing active cross-filters.

        Returns:
            str: Generated SQL query string.
        """
        v_type = visual_type.lower()
        if v_type in ("bar", "barchart"):
            visual = BarChartVisual(visual_id, table_name, config)
        elif v_type in ("line", "linechart"):
            visual = LineChartVisual(visual_id, table_name, config)
        elif v_type in ("table", "tablevisual"):
            visual = TableVisual(visual_id, table_name, config)
        elif v_type in ("kpi", "kpivisual"):
            visual = KPIVisual(visual_id, table_name, config)
        else:
            visual = BaseVisual(visual_id, table_name, config)

        return visual.generate_query(filter_context)
