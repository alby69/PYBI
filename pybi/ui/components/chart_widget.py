"""ChartWidget UI component integrating NiceGUI ECharts with Polars DataFrames."""

from typing import Any, Dict, List, Optional, Union
from nicegui import ui
import polars as pl

from pybi.dashboard import DataBinder, default_binder


class ChartWidget:
    """Reusable ChartWidget rendering ECharts in NiceGUI bound to Polars DataFrames."""

    def __init__(
        self,
        df: Optional[pl.DataFrame] = None,
        chart_type: str = "bar",
        x_col: Optional[str] = None,
        y_cols: Optional[List[str]] = None,
        title: str = "",
    ) -> None:
        """Initialize ChartWidget.

        Args:
            df: Optional Polars DataFrame containing chart data.
            chart_type: Chart type ('bar', 'line', 'pie').
            x_col: Column name for X axis or categories.
            y_cols: List of column names for Y axis values or series.
            title: Chart title.
        """
        self.chart_type = chart_type.lower()
        self.x_col = x_col
        self.y_cols = y_cols
        self.title = title
        self._df = df if df is not None else pl.DataFrame()

        # Build initial ECharts option dict
        options = self._build_options(self._df, self.chart_type, self.x_col, self.y_cols, self.title)
        self.echart = ui.echarts(options).classes("w-full h-full min-h-[220px]")

    def bind_to(
        self,
        binder: Optional[DataBinder] = None,
        widget_id: str = "chart_widget",
        source_name: str = "",
        query: Optional[str] = None,
        x_col: Optional[str] = None,
        y_cols: Optional[List[str]] = None,
        chart_type: Optional[str] = None,
    ) -> 'ChartWidget':
        """Bind this ChartWidget to a DataBinder source for reactive updates.

        Args:
            binder: DataBinder instance (defaults to default_binder).
            widget_id: Unique widget identifier.
            source_name: Name of registered data source.
            query: Optional DuckDB SQL query string.
            x_col: Optional X column override.
            y_cols: Optional Y columns override.
            chart_type: Optional chart type override.

        Returns:
            Self instance.
        """
        target_binder = binder or default_binder
        if x_col:
            self.x_col = x_col
        if y_cols:
            self.y_cols = y_cols
        if chart_type:
            self.chart_type = chart_type.lower()

        def reactive_callback(updated_df: pl.DataFrame) -> None:
            self.update_data(updated_df)

        target_binder.bind_widget(
            widget_id=widget_id,
            source_name=source_name,
            query=query,
            callback=reactive_callback,
        )

        # Initial data fetch if available
        try:
            initial_df = target_binder.get_widget_data(widget_id)
            self._df = initial_df
            options = self._build_options(self._df, self.chart_type, self.x_col, self.y_cols, self.title)
            self.echart.options.clear()
            self.echart.options.update(options)
        except Exception:
            pass

        return self

    def update_data(
        self,
        df: pl.DataFrame,
        x_col: Optional[str] = None,
        y_cols: Optional[List[str]] = None,
        chart_type: Optional[str] = None,
        title: Optional[str] = None,
    ) -> None:
        """Update chart data and refresh ECharts view.

        Args:
            df: Updated Polars DataFrame.
            x_col: Optional X column override.
            y_cols: Optional Y columns override.
            chart_type: Optional chart type override.
            title: Optional title override.
        """
        self._df = df
        if x_col is not None:
            self.x_col = x_col
        if y_cols is not None:
            self.y_cols = y_cols
        if chart_type is not None:
            self.chart_type = chart_type.lower()
        if title is not None:
            self.title = title

        options = self._build_options(self._df, self.chart_type, self.x_col, self.y_cols, self.title)
        self.echart.options.clear()
        self.echart.options.update(options)
        self.echart.update()

    @staticmethod
    def _build_options(
        df: pl.DataFrame,
        chart_type: str,
        x_col: Optional[str],
        y_cols: Optional[List[str]],
        title: str,
    ) -> Dict[str, Any]:
        """Construct ECharts options dict from Polars DataFrame.

        Args:
            df: Polars DataFrame.
            chart_type: 'bar', 'line', or 'pie'.
            x_col: Category/X column name.
            y_cols: Numeric/Y column names list.
            title: Chart title.

        Returns:
            Dict[str, Any]: ECharts configuration dictionary.
        """
        options: Dict[str, Any] = {
            "title": {"text": title, "textStyle": {"fontSize": 14, "fontWeight": "bold"}},
            "tooltip": {"trigger": "axis" if chart_type in ("bar", "line") else "item"},
            "legend": {"bottom": 0},
            "grid": {"top": 40, "bottom": 30, "left": 40, "right": 20, "containLabel": True},
        }

        if df.is_empty():
            options["series"] = []
            return options

        cols = df.columns
        # Auto-infer x_col and y_cols if not specified
        if not x_col and len(cols) > 0:
            x_col = cols[0]
        if not y_cols and len(cols) > 1:
            y_cols = cols[1:]
        elif not y_cols and len(cols) == 1:
            y_cols = [cols[0]]

        x_vals = df[x_col].to_list() if x_col and x_col in df.columns else []

        if chart_type in ("bar", "line"):
            options["xAxis"] = {"type": "category", "data": [str(v) for v in x_vals]}
            options["yAxis"] = {"type": "value"}
            series = []
            for col_name in y_cols or []:
                if col_name in df.columns:
                    series.append({
                        "name": col_name,
                        "type": chart_type,
                        "data": df[col_name].to_list(),
                        "smooth": True if chart_type == "line" else False,
                    })
            options["series"] = series

        elif chart_type == "pie":
            pie_data = []
            val_col = y_cols[0] if y_cols and y_cols[0] in df.columns else (cols[1] if len(cols) > 1 else cols[0])
            for x_val, y_val in zip(x_vals, df[val_col].to_list()):
                pie_data.append({"name": str(x_val), "value": y_val})

            options["series"] = [
                {
                    "name": val_col,
                    "type": "pie",
                    "radius": "65%",
                    "data": pie_data,
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowOffsetX": 0,
                            "shadowColor": "rgba(0, 0, 0, 0.5)",
                        }
                    },
                }
            ]

        return options
