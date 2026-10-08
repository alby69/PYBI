"""Unit and end-to-end tests for Pivot Table custom widget and DuckDB fallback binding."""

import os
import socket
import subprocess
import tempfile
import time
import urllib.request

import polars as pl
import pytest
from playwright.sync_api import expect, sync_playwright

from pybi.frontend.pivot_table import PivotTable as FrontendPivotTable
from pybi.ui.components.pivot_table import PivotTable as UIPivotTable
from pybi.ui.components.widget_data import (
    _bind_pivot_data,
    _compute_server_pivot_duckdb,
    bind_widget_data,
)


def test_pivot_table_element_config_and_data_updates():
    """Test PivotTable Python element configuration getters, setters, and data updating."""
    pt = FrontendPivotTable(
        data=[{'region': 'Europe', 'sales': 100}],
        rows=['region'],
        cols=[],
        vals=['sales'],
        aggregator_name='Sum',
    )
    assert pt.get_config() == {
        'rows': ['region'],
        'cols': [],
        'vals': ['sales'],
        'aggregator_name': 'Sum',
    }

    pt.set_config({'rows': ['category'], 'cols': ['year'], 'vals': ['profit'], 'aggregator_name': 'Average'})
    assert pt.get_config() == {
        'rows': ['category'],
        'cols': ['year'],
        'vals': ['profit'],
        'aggregator_name': 'Average',
    }

    pt.update_data([{'category': 'Tech', 'year': '2025', 'profit': 500}])
    assert pt._data == [{'category': 'Tech', 'year': '2025', 'profit': 500}]
    assert pt._columns == ['category', 'year', 'profit']

    ui_pt = UIPivotTable(rows=['a'], vals=['b'])
    assert ui_pt.get_config()['rows'] == ['a']


def test_bind_pivot_data_small_dataset():
    """Test pivot data binding for small dataset (client-side interactive data)."""
    df = pl.DataFrame({
        'region': ['Europe', 'Europe', 'North America', 'Asia Pacific'],
        'revenue': [100.0, 200.0, 300.0, 400.0],
        'units': [10, 20, 30, 40]
    })
    item = {
        'type': 'pivot',
        'rows': ['region'],
        'vals': ['revenue'],
        'aggregator_name': 'Sum',
    }
    bound = _bind_pivot_data(item, df, None)
    assert 'data' in bound
    assert len(bound['data']) == 4
    assert bound['rows'] == ['region']
    assert bound['vals'] == ['revenue']
    assert bound['aggregator_name'] == 'Sum'


def test_compute_server_pivot_duckdb():
    """Test server-side DuckDB dynamic fallback pivot matrix for large datasets."""
    df = pl.DataFrame({
        'region': ['Europe', 'Europe', 'North America', 'Asia Pacific'],
        'channel': ['Online', 'Retail', 'Online', 'Retail'],
        'revenue': [100.0, 250.0, 300.0, 450.0]
    })
    matrix = _compute_server_pivot_duckdb(
        df,
        rows=['region'],
        cols=['channel'],
        vals=['revenue'],
        agg='Sum'
    )
    assert 'colKeys' in matrix
    assert 'rows' in matrix
    assert 'colTotals' in matrix
    assert matrix['grandTotal'] == 1100.0


def test_compute_server_pivot_duckdb_multi_value_and_filters():
    """Test server-side DuckDB pivot matrix with multi-value specs and report filters."""
    df = pl.DataFrame({
        'region': ['Europe', 'Europe', 'North America', 'Asia Pacific'],
        'channel': ['Online', 'Retail', 'Online', 'Retail'],
        'revenue': [100.0, 200.0, 300.0, 400.0],
        'units': [10, 20, 30, 40]
    })
    vals = [
        {'field': 'revenue', 'agg': 'Sum', 'showAs': 'None'},
        {'field': 'units', 'agg': 'Average', 'showAs': 'None'}
    ]
    matrix = _compute_server_pivot_duckdb(
        df,
        rows=['region'],
        cols=['channel'],
        vals=vals,
        filters=['region'],
        filter_values={'region': 'Europe'}
    )
    assert len(matrix['rows']) == 1
    assert matrix['rows'][0]['rowKey'] == ['Europe']
    assert 'valueSpecs' in matrix
    assert len(matrix['valueSpecs']) == 2


def test_bind_pivot_data_large_dataset_fallback():
    """Test that datasets >50,000 rows automatically trigger DuckDB server-side fallback."""
    n = 50005
    df = pl.DataFrame({
        'region': ['EU' if i % 2 == 0 else 'US' for i in range(n)],
        'sales': [10.0 for _ in range(n)]
    })
    item = {
        'type': 'pivot',
        'rows': ['region'],
        'vals': ['sales'],
        'aggregator_name': 'Sum',
    }
    bound = _bind_pivot_data(item, df, None)
    assert 'server_pivot_data' in bound
    assert bound['server_pivot_data']['grandTotal'] == n * 10.0


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@pytest.fixture(scope='module')
def data_dir():
    return tempfile.mkdtemp()


@pytest.fixture(scope='module')
def server(data_dir):
    port = get_free_port()
    env = os.environ.copy()
    env['NICEGUI_SCREEN_TEST_PORT'] = str(port)
    env['DATA_DIR'] = data_dir
    log_f = tempfile.NamedTemporaryFile(mode='w+', delete=False)
    proc = subprocess.Popen(
        ['python3', '-m', 'pybi.main', '--port', str(port)],
        env=env,
        stdout=log_f,
        stderr=log_f,
    )
    try:
        url = f'http://127.0.0.1:{port}'
        req = urllib.request.Request(f'{url}/dashboard-editor', headers={'User-Agent': 'Mozilla/5.0'})
        for _ in range(40):
            try:
                if urllib.request.urlopen(req).status == 200:
                    break
            except Exception:
                time.sleep(0.5)
        else:
            with open(log_f.name) as f:
                pytest.fail(f'Server failed to start:\n{f.read()}')
        yield url
    finally:
        proc.terminate()
        proc.wait()


@pytest.fixture(scope='module')
def page(server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        browser_page = browser.new_page()
        browser_page.on('pageerror', lambda err: print(f'BROWSER UNCAUGHT EXCEPTION: {err}'))
        browser_page.goto(f'{server}/dashboard-editor')
        browser_page.wait_for_selector('.vgl-item:not(.vgl-item--placeholder)', timeout=20000)
        yield browser_page
        browser.close()


def test_pivot_table_e2e_creation_and_rendering(page):
    """Playwright E2E test verifying Pivot Table widget creation and rendering."""
    # Add a new Pivot Table widget
    page.get_by_role('button', name='Add Widget').click()
    drawer = page.locator('.q-drawer', has_text='Add Widget')
    expect(drawer).to_be_visible()

    drawer.get_by_label('Widget Title').fill('Regional Sales Pivot')
    drawer.locator('.q-select', has_text='Widget Type').click()
    page.get_by_role('option', name='pivot').click()

    drawer.get_by_label('Rows Fields (comma-separated)').fill('region')
    drawer.get_by_label('Values Fields (comma-separated)').fill('revenue')
    drawer.get_by_role('button', name='Apply').click()

    expect(drawer).not_to_be_visible()

    # Check pivot widget appears on dashboard
    pivot_item = page.locator('.vgl-item', has_text='Regional Sales Pivot')
    expect(pivot_item).to_be_visible()

    # Verify pivoted rows and aggregates render in DOM
    expect(pivot_item.get_by_text('Europe')).to_be_visible()
    expect(pivot_item.get_by_text('North America')).to_be_visible()
    expect(pivot_item.get_by_text('Grand Total').first).to_be_visible()
