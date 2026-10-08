"""Shared widget data binding helpers for dashboard layouts (editor and viewer)."""

import copy
import math
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import polars as pl

from pybi.dashboard import default_binder

MAX_TABLE_ROWS = 50
MAX_CHART_POINTS = 60
MAX_CHART_SERIES = 3
KPI_METRICS = ('sum', 'avg', 'min', 'max', 'count')
KPI_METHODS = {'sum': 'sum', 'avg': 'mean', 'min': 'min', 'max': 'max'}
WIDGET_DATA_KEYS = (
    'columns', 'rows_data', 'rows', 'cols', 'vals', 'row_count', 'truncated',
    'data_error', 'chart', 'kpi', 'data', 'server_pivot_data'
)

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
    item['rows_data'] = [[_cell(v) for v in row] for row in view.rows()]
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


def _compute_server_pivot_duckdb(df: pl.DataFrame, rows: List[str], cols: List[str], vals: List[str], agg: str) -> Dict[str, Any]:
    """Execute server-side DuckDB GROUP BY query for large datasets."""
    conn = duckdb.connect(':memory:')
    from pybi.etl.executor import configure_duckdb_connection
    configure_duckdb_connection(conn)
    conn.register('source_tbl', df)

    agg_func = agg.upper() if agg else 'SUM'
    if agg_func == 'AVERAGE':
        agg_func = 'AVG'
    if agg_func not in ('SUM', 'COUNT', 'AVG', 'MIN', 'MAX'):
        agg_func = 'SUM'

    valid_cols = set(df.columns)
    r_fields = [r for r in rows if r in valid_cols]
    c_fields = [c for c in cols if c in valid_cols]
    v_fields = [v for v in vals if v in valid_cols]

    group_fields = r_fields + c_fields

    if v_fields and agg_func != 'COUNT':
        val_expr = f'"{v_fields[0]}"'
        agg_sql = f"{agg_func}({val_expr})"
    else:
        agg_sql = "COUNT(*)"

    if not group_fields:
        q = f"SELECT {agg_sql} AS agg_val FROM source_tbl"
        res = conn.execute(q).fetchall()
        val = float(res[0][0]) if res and res[0][0] is not None else 0.0
        return {
            'colKeys': [[]],
            'rows': [{'rowKey': [], 'cells': [val], 'rowTotal': val}],
            'colTotals': [val],
            'grandTotal': val
        }

    group_str = ", ".join([f'"{g}"' for g in group_fields])
    q = f"SELECT {group_str}, {agg_sql} AS agg_val FROM source_tbl GROUP BY {group_str}"
    res_df = conn.execute(q).pl()

    row_keys_set = set()
    col_keys_set = set()

    for row in res_df.rows():
        r_key = [str(row[i]) if row[i] is not None else '' for i in range(len(r_fields))]
        c_key = [str(row[len(r_fields) + j]) if row[len(r_fields) + j] is not None else '' for j in range(len(c_fields))]
        row_keys_set.add(tuple(r_key))
        col_keys_set.add(tuple(c_key))

    row_keys = list(row_keys_set)
    col_keys = list(col_keys_set)

    cell_map = {}
    for row in res_df.rows():
        r_key = tuple([str(row[i]) if row[i] is not None else '' for i in range(len(r_fields))])
        c_key = tuple([str(row[len(r_fields) + j]) if row[len(r_fields) + j] is not None else '' for j in range(len(c_fields))])
        val = row[-1]
        cell_map[(r_key, c_key)] = float(val) if val is not None else None

    matrix_rows = []
    col_totals_sum = [0.0] * len(col_keys)
    col_totals_count = [0] * len(col_keys)
    grand_sum = 0.0
    grand_count = 0

    for r_key in row_keys:
        cells = []
        row_sum = 0.0
        row_count = 0
        for c_idx, c_key in enumerate(col_keys):
            cell_val = cell_map.get((r_key, c_key))
            cells.append(cell_val)
            if cell_val is not None:
                row_sum += cell_val
                row_count += 1
                col_totals_sum[c_idx] += cell_val
                col_totals_count[c_idx] += 1
                grand_sum += cell_val
                grand_count += 1

        row_total = row_sum if row_count > 0 else None
        matrix_rows.append({
            'rowKey': list(r_key),
            'cells': cells,
            'rowTotal': row_total
        })

    col_totals = [col_totals_sum[i] if col_totals_count[i] > 0 else None for i in range(len(col_keys))]
    grand_total = grand_sum if grand_count > 0 else None

    return {
        'colKeys': [list(ck) for ck in col_keys],
        'rows': matrix_rows,
        'colTotals': col_totals,
        'grandTotal': grand_total
    }


def _bind_pivot_data(item: Dict[str, Any], df: pl.DataFrame, error: Optional[str]) -> Dict[str, Any]:
    """Attach pivot dataset records or server-side DuckDB pre-aggregated pivot matrix."""
    if error is not None:
        item['columns'] = []
        item['data_error'] = error
        return item

    if df.is_empty():
        item['columns'] = [str(c) for c in df.columns]
        item['data_error'] = 'Source DataFrame is empty'
        return item

    all_cols = [str(c) for c in df.columns]
    rows = item.get('rows') if isinstance(item.get('rows'), list) else []
    cols = item.get('cols') if isinstance(item.get('cols'), list) else []
    vals = item.get('vals') if isinstance(item.get('vals'), list) else []
    agg = item.get('aggregator_name') or item.get('aggregatorName') or 'Sum'

    if not rows and not cols and all_cols:
        rows = [all_cols[0]]
    if not vals:
        numeric = [c for c in df.columns if df[c].dtype.is_numeric()]
        if numeric:
            vals = [numeric[0]]

    item['rows'] = rows
    item['cols'] = cols
    item['vals'] = vals
    item['aggregator_name'] = agg
    item['columns'] = all_cols

    if df.height > 50000:
        item['server_pivot_data'] = _compute_server_pivot_duckdb(df, rows, cols, vals, agg)
    else:
        view = df.head(10000)
        item['data'] = [{c: _cell(v) for c, v in zip(all_cols, row)} for row in view.rows()]

    return item


def _bind_widget_data(widget: Dict[str, Any]) -> Dict[str, Any]:
    """Attach live data pulled from the widget's bound source."""
    item = {k: v for k, v in widget.items() if k not in WIDGET_DATA_KEYS}
    for key in ('rows', 'cols', 'vals', 'aggregator_name'):
        if key in widget:
            item[key] = widget[key]

    widget_type = item.get('type')
    if widget_type not in ('table', 'chart', 'kpi', 'pivot'):
        return item
    df, error = _source_frame(item)
    if widget_type == 'table':
        return _bind_table_data(item, df, error)
    if widget_type == 'chart':
        return _bind_chart_data(item, df, error)
    if widget_type == 'pivot':
        return _bind_pivot_data(item, df, error)
    return _bind_kpi_data(item, df, error)


def bind_widget_data(layout: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a copy of the layout with live data attached to every widget."""
    register_sample_source()
    return [_bind_widget_data(item) for item in layout]


def strip_widget_data(layout: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a copy of the layout without the live data (for storage/export)."""
    return [{k: v for k, v in item.items() if k not in WIDGET_DATA_KEYS} for item in layout]
