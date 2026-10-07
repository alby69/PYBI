"""Shared widget data binding helpers for dashboard layouts (editor and viewer)."""

import copy
import math
from typing import Any, Dict, List, Optional, Tuple

import polars as pl

from pybi.dashboard import default_binder

MAX_TABLE_ROWS = 50
MAX_CHART_POINTS = 60
MAX_CHART_SERIES = 3
KPI_METRICS = ('sum', 'avg', 'min', 'max', 'count')
KPI_METHODS = {'sum': 'sum', 'avg': 'mean', 'min': 'min', 'max': 'max'}
WIDGET_DATA_KEYS = ('columns', 'rows', 'row_count', 'truncated', 'data_error', 'chart', 'kpi')

SAMPLE_LAYOUT = [
    {
        'i': 'w1',
        'x': 0, 'y': 0, 'w': 4, 'h': 3,
        'title': '📊 Quarterly Revenue',
        'type': 'kpi',
        'metric': 'sum',
        'source': 'regional_sales'
    },
    {
        'i': 'w2',
        'x': 4, 'y': 0, 'w': 8, 'h': 4,
        'title': '📈 Regional Sales Bar Chart',
        'type': 'chart',
        'chartType': 'bar',
        'source': 'regional_sales'
    },
    {
        'i': 'w3',
        'x': 0, 'y': 3, 'w': 4, 'h': 4,
        'title': '📋 Top Performing Regions',
        'type': 'table',
        'source': 'regional_sales'
    }
]


def register_sample_source() -> None:
    """Register the built-in 'regional_sales' sample source when not already present."""
    try:
        default_binder.get_source_data('regional_sales')
    except KeyError:
        sample_df = pl.DataFrame({
            'region': ['Europe', 'North America', 'Asia Pacific', 'Latin America'],
            'revenue': [1200, 1850, 950, 420],
            'units_sold': [120, 190, 85, 45]
        })
        default_binder.register_source('regional_sales', sample_df)


def sample_layout() -> List[Dict[str, Any]]:
    """Return a deep copy of the demo dashboard layout (unbound)."""
    return copy.deepcopy(SAMPLE_LAYOUT)


def available_sources() -> List[str]:
    """Registered data source names usable as widget bindings."""
    try:
        names = default_binder.list_sources()
    except Exception:
        names = []
    return names or ['regional_sales']


def _cell(value):
    """Make a DataFrame value JSON serializable for the browser."""
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return str(value)


def _number(value):
    """Coerce a numeric cell to a JSON-safe float, or None when not plottable."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return value if math.isfinite(value) else None
    return None


def _format_number(value):
    """Pretty-print an aggregated metric value."""
    if value is None:
        return None
    if isinstance(value, int):
        return f'{value:,}'
    as_float = float(value)
    if as_float == int(as_float):
        return f'{int(as_float):,}'
    return f'{as_float:,.2f}'


def _source_frame(item: Dict[str, Any]) -> Tuple[Optional[pl.DataFrame], Optional[str]]:
    """Fetch the widget's bound DataFrame, or return (None, error message)."""
    source = item.get('source')
    if not source:
        return None, 'No data source selected'
    try:
        return default_binder.get_source_data(source), None
    except KeyError:
        return None, f'Unknown source "{source}" - run the ETL pipeline first'
    except Exception as err:
        return None, f'Failed to load source "{source}": {err}'


def _bind_table_data(item: Dict[str, Any], df: pl.DataFrame, error: Optional[str]) -> Dict[str, Any]:
    if error is not None:
        item['columns'] = []
        item['data_error'] = error
        return item
    view = df.head(MAX_TABLE_ROWS)
    item['columns'] = [str(c) for c in view.columns]
    item['rows'] = [[_cell(v) for v in row] for row in view.rows()]
    item['row_count'] = df.height
    item['truncated'] = df.height > MAX_TABLE_ROWS
    return item


def _bind_chart_data(item: Dict[str, Any], df: pl.DataFrame, error: Optional[str]) -> Dict[str, Any]:
    kind = item.get('chartType')
    kind = kind if kind in ('bar', 'line', 'pie') else 'bar'
    chart = {'kind': kind, 'labels': [], 'series': [], 'max': 0}
    item['chart'] = chart
    if error is not None:
        chart['error'] = error
        return item
    view = df.head(MAX_CHART_POINTS)
    if view.is_empty():
        chart['error'] = 'Source is empty'
        return item
    numeric = [c for c in view.columns if view[c].dtype.is_numeric()]
    if not numeric:
        chart['error'] = f'Source has no numeric column to plot ({", ".join(view.columns)})'
        return item
    label_col = next((c for c in view.columns if c not in numeric), None)
    if label_col is not None:
        chart['labels'] = [str(v) for v in view[label_col].to_list()]
    else:
        chart['labels'] = [str(i) for i in range(view.height)]
    for name in numeric[:MAX_CHART_SERIES]:
        values = [_number(v) for v in view[name].to_list()]
        chart['series'].append({'name': name, 'values': values})
    plottable = [v for s in chart['series'] for v in s['values'] if v is not None]
    chart['max'] = max(plottable) if plottable else 0
    if chart['max'] <= 0:
        chart['max'] = 1
    if view.height > MAX_CHART_POINTS:
        chart['truncated'] = True
    return item


def _bind_kpi_data(item: Dict[str, Any], df: pl.DataFrame, error: Optional[str]) -> Dict[str, Any]:
    metric = item.get('metric') if item.get('metric') in KPI_METRICS else 'sum'
    source = item.get('source')
    if error is not None:
        item['kpi'] = {'value': None, 'subtitle': error, 'error': True}
        return item
    if metric == 'count':
        item['kpi'] = {'value': _format_number(df.height), 'subtitle': f'rows from {source}'}
        return item
    numeric = [c for c in df.columns if df[c].dtype.is_numeric()]
    if not numeric:
        item['kpi'] = {'value': None, 'subtitle': f'No numeric column in {source} for {metric}', 'error': True}
        return item
    column = numeric[0]
    raw = getattr(df[column], KPI_METHODS[metric])()
    value = _format_number(raw)
    item['kpi'] = {'value': value, 'subtitle': f'{metric} of {column} from {source}'}
    return item


def _bind_widget_data(widget: Dict[str, Any]) -> Dict[str, Any]:
    """Attach live data pulled from the widget's bound source."""
    item = {k: v for k, v in widget.items() if k not in WIDGET_DATA_KEYS}
    widget_type = item.get('type')
    if widget_type not in ('table', 'chart', 'kpi'):
        return item
    df, error = _source_frame(item)
    if widget_type == 'table':
        return _bind_table_data(item, df, error)
    if widget_type == 'chart':
        return _bind_chart_data(item, df, error)
    return _bind_kpi_data(item, df, error)


def bind_widget_data(layout: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a copy of the layout with live data attached to every widget."""
    register_sample_source()
    return [_bind_widget_data(item) for item in layout]


def strip_widget_data(layout: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a copy of the layout without the live data (for storage/export)."""
    return [{k: v for k, v in item.items() if k not in WIDGET_DATA_KEYS} for item in layout]