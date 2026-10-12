"""Chart components providing NiceGUI wrappers for bar and line charts bound to DataBinder."""

from typing import Any, Dict, List, Optional, Union
from nicegui import ui
import polars as pl

from pybi.dashboard.binding import DataBinder, default_binder
from pybi.ui.components.chart_widget import ChartWidget


class Chart:
    """Generic NiceGUI chart wrapper bound automatically to DataBinder."""

    def __init__(
        self,
        widget_id: str,
        source_name: str = "",
        chart_type: str = "bar",
        x_col: Optional[str] = None,
        y_cols: Optional[List[str]] = None,
        title: str = "",
        query: Optional[str] = None,
        binder: Optional[DataBinder] = None,
    ) -> None:
        """Initialize Chart component.

        Args:
            widget_id: Unique identifier for widget in DataBinder.
            source_name: Registered data source name in DataBinder.
            chart_type: Chart type ('bar', 'line', 'pie').
            x_col: Column name for X axis / categories.
            y_cols: List of column names for Y axis values.
            title: Title string for chart widget.
            query: Optional SQL query for DuckDB evaluation.
            binder: DataBinder instance (defaults to default_binder).
        """
        self.widget_id = widget_id
        self.source_name = source_name
        self.chart_type = chart_type.lower()
        self.x_col = x_col
        self.y_cols = y_cols
        self.title = title
        self.query = query
        self.binder = binder or default_binder

        self._widget = ChartWidget(
            df=pl.DataFrame(),
            chart_type=self.chart_type,
            x_col=self.x_col,
            y_cols=self.y_cols,
            title=self.title,
        )

        if self.source_name:
            self.bind_source(
                source_name=self.source_name,
                query=self.query,
                x_col=self.x_col,
                y_cols=self.y_cols,
            )

    def bind_source(
        self,
        source_name: str,
        query: Optional[str] = None,
        x_col: Optional[str] = None,
        y_cols: Optional[List[str]] = None,
    ) -> "Chart":
        """Bind or re-bind chart to a DataBinder source name.

        Args:
            source_name: Data source identifier in DataBinder.
            query: Optional SQL query string.
            x_col: Optional X column override.
            y_cols: Optional Y column list override.

        Returns:
            Self instance.
        """
        self.source_name = source_name
        self.query = query
        if x_col:
            self.x_col = x_col
        if y_cols:
            self.y_cols = y_cols

        self._widget.bind_to(
            binder=self.binder,
            widget_id=self.widget_id,
            source_name=self.source_name,
            query=self.query,
            x_col=self.x_col,
            y_cols=self.y_cols,
            chart_type=self.chart_type,
        )
        return self

    def update_data(self, df: pl.DataFrame) -> None:
        """Manually trigger chart data update.

        Args:
            df: New Polars DataFrame.
        """
        self._widget.update_data(
            df,
            x_col=self.x_col,
            y_cols=self.y_cols,
            chart_type=self.chart_type,
            title=self.title,
        )

    @property
    def dataframe(self) -> pl.DataFrame:
        """Get the current underlying DataFrame."""
        return self._widget._df


class BarChart(Chart):
    """Specialized Bar Chart component auto-registered with DataBinder."""

    def __init__(
        self,
        widget_id: str,
        source_name: str = "",
        x_col: Optional[str] = None,
        y_cols: Optional[List[str]] = None,
        title: str = "",
        query: Optional[str] = None,
        binder: Optional[DataBinder] = None,
    ) -> None:
        """Initialize BarChart.

        Args:
            widget_id: Widget identifier string.
            source_name: Source name registered in DataBinder.
            x_col: Category/X column name.
            y_cols: Value/Y column names.
            title: Chart title.
            query: DuckDB SQL query.
            binder: DataBinder instance.
        """
        super().__init__(
            widget_id=widget_id,
            source_name=source_name,
            chart_type="bar",
            x_col=x_col,
            y_cols=y_cols,
            title=title,
            query=query,
            binder=binder,
        )


class LineChart(Chart):
    """Specialized Line Chart component auto-registered with DataBinder."""

    def __init__(
        self,
        widget_id: str,
        source_name: str = "",
        x_col: Optional[str] = None,
        y_cols: Optional[List[str]] = None,
        title: str = "",
        query: Optional[str] = None,
        binder: Optional[DataBinder] = None,
    ) -> None:
        """Initialize LineChart.

        Args:
            widget_id: Widget identifier string.
            source_name: Source name registered in DataBinder.
            x_col: Category/X column name.
            y_cols: Value/Y column names.
            title: Chart title.
            query: DuckDB SQL query.
            binder: DataBinder instance.
        """
        super().__init__(
            widget_id=widget_id,
            source_name=source_name,
            chart_type="line",
            x_col=x_col,
            y_cols=y_cols,
            title=title,
            query=query,
            binder=binder,
        )


if __name__ == "__main__":
    # Manual standalone test
    print("Testing charts.py standalone...")
    binder = DataBinder()
    sample_df = pl.DataFrame({
        "category": ["A", "B", "C"],
        "values": [10, 20, 30]
    })
    binder.register_source("sample_src", sample_df)

    bar = BarChart(widget_id="test_bar", source_name="sample_src", x_col="category", y_cols=["values"], title="Test Bar", binder=binder)
    print("BarChart initial rows:", len(bar.dataframe))
    assert len(bar.dataframe) == 3

    # Update source in binder
    binder.update_source("sample_src", pl.DataFrame({"category": ["A", "B"], "values": [100, 200]}))
    print("BarChart after reactive update rows:", len(bar.dataframe))
    assert len(bar.dataframe) == 2
    print("charts.py self-test passed!")
