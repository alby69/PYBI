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
    'columns', 'rows_data', 'rows', 'cols', 'vals', 'values', 'filters', 'filter_values',
    'showRowSubtotals', 'showColSubtotals', 'showGrandTotals', 'emptyValuePlaceholder',
    'row_count', 'truncated', 'data_error', 'chart', 'kpi', 'data', 'server_pivot_data'
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


def _build_vega_lite_spec(kind: str, labels: List[str], series: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a declarative Vega-Lite specification dict."""
    data_values = []
    for idx, label in enumerate(labels):
        row = {'category': label}
        for s in series:
            val = s['values'][idx] if idx < len(s['values']) else None
            row[s['name']] = val
        data_values.append(row)

    mark_type = 'bar' if kind == 'bar' else ('line' if kind == 'line' else 'arc')

    if kind == 'pie' and series:
        val_col = series[0]['name']
        encoding = {
            'theta': {'field': val_col, 'type': 'quantitative'},
            'color': {'field': 'category', 'type': 'nominal'},
        }
    elif series and len(series) == 1:
        val_col = series[0]['name']
        encoding = {
            'x': {'field': 'category', 'type': 'nominal'},
            'y': {'field': val_col, 'type': 'quantitative'},
        }
    else:
        encoding = {
            'x': {'field': 'category', 'type': 'nominal'},
            'y': {'field': 'value', 'type': 'quantitative'},
            'color': {'field': 'series', 'type': 'nominal'},
        }

    return {
        '$schema': 'https://vega.github.io/schema/vega-lite/v5.json',
        'mark': mark_type,
        'data': {'values': data_values},
        'encoding': encoding,
    }


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

    chart['vega_lite_spec'] = _build_vega_lite_spec(kind, chart['labels'], chart['series'])
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


def _normalize_value_specs(vals: Any, default_agg: str = 'Sum') -> List[Dict[str, Any]]:
    """Normalize values config into a list of value spec dicts: [{field, agg, showAs}]."""
    if not vals:
        return []
    if isinstance(vals, list):
        specs = []
        for v in vals:
            if isinstance(v, dict):
                field = v.get('field') or v.get('col') or v.get('name') or ''
                agg = v.get('agg') or v.get('aggregatorName') or default_agg
                show_as = v.get('showAs') or 'None'
                if field:
                    specs.append({'field': field, 'agg': agg, 'showAs': show_as})
            elif isinstance(v, str) and v.strip():
                specs.append({'field': v.strip(), 'agg': default_agg, 'showAs': 'None'})
        return specs
    elif isinstance(vals, str) and vals.strip():
        return [{'field': vals.strip(), 'agg': default_agg, 'showAs': 'None'}]
    return []


def _compute_server_pivot_duckdb(
    df: pl.DataFrame,
    rows: List[str],
    cols: List[str],
    vals: Any,
    agg: str = 'Sum',
    filters: Optional[List[str]] = None,
    filter_values: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute server-side DuckDB GROUP BY query for large datasets."""
    conn = duckdb.connect(':memory:')
    from pybi.etl.executor import configure_duckdb_connection
    configure_duckdb_connection(conn)
    conn.register('source_tbl', df)

    valid_cols = set(df.columns)
    r_fields = [r for r in (rows or []) if r in valid_cols]
    c_fields = [c for c in (cols or []) if c in valid_cols]
    val_specs = _normalize_value_specs(vals, default_agg=agg)
    val_specs = [v for v in val_specs if v['field'] in valid_cols]

    # Filter conditions
    where_clauses = []
    if filter_values and isinstance(filter_values, dict):
        for f_col, f_val in filter_values.items():
            if f_col in valid_cols and f_val is not None and str(f_val).strip() != '':
                safe_val = str(f_val).replace("'", "''")
                where_clauses.append(f'"{f_col}" = \'{safe_val}\'')

    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    group_fields = r_fields + c_fields

    if not val_specs:
        val_specs = [{'field': valid_cols.pop() if valid_cols else 'val', 'agg': 'Count', 'showAs': 'None'}]

    select_exprs = [f'"{g}"' for g in group_fields]
    for idx, spec in enumerate(val_specs):
        v_col = spec['field']
        v_agg = spec['agg'].upper() if spec['agg'] else 'SUM'
        if v_agg == 'AVERAGE':
            v_agg = 'AVG'
        if v_agg not in ('SUM', 'COUNT', 'AVG', 'MIN', 'MAX'):
            v_agg = 'SUM'

        if v_agg == 'COUNT':
            select_exprs.append(f"COUNT(*) AS val_{idx}")
        else:
            select_exprs.append(f"{v_agg}(\"{v_col}\") AS val_{idx}")

    if not group_fields:
        q = f"SELECT {', '.join(select_exprs[len(group_fields):])} FROM source_tbl{where_sql}"
        res = conn.execute(q).fetchall()
        cells = [float(res[0][i]) if res and res[0][i] is not None else 0.0 for i in range(len(val_specs))]
        return {
            'valueSpecs': val_specs,
            'colKeys': [[]],
            'rows': [{'rowKey': [], 'cells': cells, 'rowTotal': cells[0]}],
            'colTotals': cells,
            'grandTotal': cells[0]
        }

    group_str = ", ".join([f'"{g}"' for g in group_fields])
    q = f"SELECT {', '.join(select_exprs)} FROM source_tbl{where_sql} GROUP BY {group_str}"
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
        vals_tuple = tuple(float(row[len(group_fields) + k]) if row[len(group_fields) + k] is not None else None for k in range(len(val_specs)))
        cell_map[(r_key, c_key)] = vals_tuple

    # Expand colKeys for multi-value specs if val_specs > 1 or c_fields > 0
    expanded_col_keys = []
    if c_fields and len(val_specs) > 1:
        for c_key in col_keys:
            for spec in val_specs:
                expanded_col_keys.append(list(c_key) + [f"{spec['field']} ({spec['agg']})"])
    elif c_fields:
        expanded_col_keys = [list(ck) for ck in col_keys]
    elif len(val_specs) > 1:
        expanded_col_keys = [[f"{spec['field']} ({spec['agg']})"] for spec in val_specs]
    else:
        expanded_col_keys = [[]]

    matrix_rows = []
    for r_key in row_keys:
        cells = []
        if c_fields and len(val_specs) > 1:
            for c_key in col_keys:
                vals_tuple = cell_map.get((r_key, c_key), (None,) * len(val_specs))
                cells.extend(vals_tuple)
        elif c_fields:
            for c_key in col_keys:
                vals_tuple = cell_map.get((r_key, c_key), (None,))
                cells.append(vals_tuple[0])
        elif len(val_specs) > 1:
            vals_tuple = cell_map.get((r_key, ()), (None,) * len(val_specs))
            cells.extend(vals_tuple)
        else:
            vals_tuple = cell_map.get((r_key, ()), (None,))
            cells.append(vals_tuple[0])

        valid_cells = [c for c in cells if c is not None]
        row_total = sum(valid_cells) if valid_cells else None
        matrix_rows.append({
            'rowKey': list(r_key),
            'cells': cells,
            'rowTotal': row_total
        })

    col_totals = []
    num_cols = len(matrix_rows[0]['cells']) if matrix_rows else 0
    for c_i in range(num_cols):
        col_vals = [r['cells'][c_i] for r in matrix_rows if r['cells'][c_i] is not None]
        col_totals.append(sum(col_vals) if col_vals else None)

    valid_col_totals = [ct for ct in col_totals if ct is not None]
    grand_total = sum(valid_col_totals) if valid_col_totals else None

    return {
        'valueSpecs': val_specs,
        'colKeys': expanded_col_keys,
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
    vals = item.get('values') or item.get('vals') or []
    filters = item.get('filters') if isinstance(item.get('filters'), list) else []
    filter_values = item.get('filter_values') if isinstance(item.get('filter_values'), dict) else {}
    agg = item.get('aggregator_name') or item.get('aggregatorName') or 'Sum'

    if not rows and not cols and all_cols:
        rows = [all_cols[0]]

    item['rows'] = rows
    item['cols'] = cols
    item['vals'] = vals
    item['values'] = vals
    item['filters'] = filters
    item['filter_values'] = filter_values
    item['aggregator_name'] = agg
    item['columns'] = all_cols

    if df.height > 50000:
        item['server_pivot_data'] = _compute_server_pivot_duckdb(
            df, rows=rows, cols=cols, vals=vals, agg=agg, filters=filters, filter_values=filter_values
        )
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
