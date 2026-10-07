"""End-to-end test for Dashboard Editor widget creation, editing and deletion."""

import os
import socket
import subprocess
import tempfile
import time
import urllib.request

import pytest
from playwright.sync_api import expect, sync_playwright


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@pytest.fixture(scope='module')
def data_dir():
    """Isolated DATA_DIR shared by the server fixture."""
    return tempfile.mkdtemp()


@pytest.fixture(scope='module')
def server(data_dir):
    """Start the PyBI server in a subprocess with isolated storage and yield its base URL."""
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
    """Open the Dashboard Editor in a headless browser."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        browser_page = browser.new_page()
        browser_page.on('pageerror', lambda err: print(f'BROWSER UNCAUGHT EXCEPTION: {err}'))
        browser_page.goto(f'{server}/dashboard-editor')
        browser_page.wait_for_selector('.vgl-item:not(.vgl-item--placeholder)', timeout=20000)
        yield browser_page
        browser.close()


def widget_items(page):
    """Rendered widgets, ignoring the grid layout placeholder item."""
    return page.locator('.vgl-item:not(.vgl-item--placeholder)')


def widget(page, title):
    """Locate a rendered grid widget whose text contains the given title."""
    return page.locator('.vgl-item', has_text=title)


def configurator_drawer(page, marker):
    """Locate the widget configurator right drawer identified by its header marker."""
    return page.locator('.q-drawer', has_text=marker)


def test_demo_widgets_shown_when_nothing_was_saved(page):
    expect(widget_items(page)).to_have_count(3)
    expect(widget(page, 'Quarterly Revenue')).to_be_visible()
    expect(widget(page, 'Quarterly Revenue').get_by_text('4,420')).to_be_visible()


def test_add_widget_appends_a_new_item(page):
    before = widget_items(page).count()

    page.get_by_role('button', name='Add Widget').click()
    drawer = configurator_drawer(page, 'Add Widget')
    expect(drawer).to_be_visible()

    drawer.get_by_label('Widget Title').fill('Revenue Forecast')
    drawer.get_by_role('button', name='Apply').click()

    expect(drawer).not_to_be_visible()
    expect(widget_items(page)).to_have_count(before + 1)
    expect(widget(page, 'Revenue Forecast')).to_be_visible()


def test_pencil_button_opens_configurator(page):
    widget(page, 'Revenue Forecast').locator('.edit-widget-btn').click()

    drawer = configurator_drawer(page, 'Configure: Revenue Forecast')
    expect(drawer).to_be_visible()
    drawer.get_by_label('Widget Title').fill('Forecast 2026')
    drawer.get_by_role('button', name='Apply').click()

    expect(drawer).not_to_be_visible()
    expect(widget(page, 'Forecast 2026')).to_be_visible()


def test_delete_widget_removes_it_from_canvas(page):
    before = widget_items(page).count()

    widget(page, 'Forecast 2026').locator('.edit-widget-btn').click()
    drawer = configurator_drawer(page, 'Configure: Forecast 2026')
    expect(drawer).to_be_visible()

    drawer.get_by_role('button', name='Delete').click()

    expect(drawer).not_to_be_visible()
    expect(widget_items(page)).to_have_count(before - 1)
    expect(widget(page, 'Forecast 2026')).to_have_count(0)


def test_undo_restores_deleted_widget(page):
    before = widget_items(page).count()

    page.locator('.q-btn').filter(has_text='undo').first.click()

    expect(widget_items(page)).to_have_count(before + 1)
    expect(widget(page, 'Forecast 2026')).to_be_visible()


def test_saved_layout_is_restored_after_reload(page):
    page.get_by_role('button', name='Save Layout').click()
    page.wait_for_timeout(700)

    page.reload()
    page.wait_for_selector('.vgl-item:not(.vgl-item--placeholder)', timeout=20000)

    expect(widget(page, 'Forecast 2026')).to_be_visible()
    expect(widget(page, 'Quarterly Revenue')).to_be_visible()


def test_table_widget_renders_columns_of_bound_source(page):
    demo = widget(page, 'Top Performing Regions')
    expect(demo.get_by_text('units_sold')).to_be_visible()
    expect(demo.get_by_text('$45,200')).to_have_count(0)

    page.get_by_role('button', name='Add Widget').click()
    drawer = configurator_drawer(page, 'Add Widget')
    expect(drawer).to_be_visible()

    drawer.get_by_label('Widget Title').fill('Bound Regions Table')
    drawer.locator('.q-select', has_text='Widget Type').click()
    page.get_by_role('option', name='table').click()
    drawer.get_by_role('button', name='Apply').click()

    expect(drawer).not_to_be_visible()
    bound = widget(page, 'Bound Regions Table')
    expect(bound).to_be_visible()
    expect(bound.get_by_role('columnheader', name='region')).to_be_visible()
    expect(bound.get_by_role('columnheader', name='revenue')).to_be_visible()
    expect(bound.get_by_role('cell', name='Europe')).to_be_visible()


def test_chart_widget_renders_data_from_bound_source(page):
    chart = widget(page, 'Regional Sales Bar Chart')
    expect(chart.get_by_text('Europe', exact=True)).to_be_visible()
    expect(chart.locator('.bg-blue-500')).to_have_count(0)


def test_pie_chart_widget_renders_slices(page):
    page.get_by_role('button', name='Add Widget').click()
    drawer = configurator_drawer(page, 'Add Widget')
    expect(drawer).to_be_visible()

    drawer.get_by_label('Widget Title').fill('Sales Pie')
    drawer.locator('.q-select', has_text='Widget Type').click()
    page.get_by_role('option', name='chart').click()
    drawer.locator('.q-select', has_text='Chart Style').click()
    page.get_by_role('option', name='pie').click()
    drawer.get_by_role('button', name='Apply').click()

    expect(drawer).not_to_be_visible()
    pie = widget(page, 'Sales Pie')
    expect(pie).to_be_visible()
    expect(pie.locator('svg path')).to_have_count(4)
    expect(pie.get_by_text('Latin America')).to_be_visible()


def test_kpi_widget_shows_aggregate_of_bound_source(page):
    page.get_by_role('button', name='Add Widget').click()
    drawer = configurator_drawer(page, 'Add Widget')
    expect(drawer).to_be_visible()

    drawer.get_by_label('Widget Title').fill('Revenue Sum')
    drawer.get_by_role('button', name='Apply').click()

    expect(drawer).not_to_be_visible()
    kpi = widget(page, 'Revenue Sum')
    expect(kpi.get_by_text('4,420')).to_be_visible()
    expect(kpi.get_by_text('sum of revenue')).to_be_visible()


def test_kpi_avg_metric_uses_the_binding(page):
    page.get_by_role('button', name='Add Widget').click()
    drawer = configurator_drawer(page, 'Add Widget')
    expect(drawer).to_be_visible()

    drawer.get_by_label('Widget Title').fill('Revenue Avg')
    drawer.locator('.q-select', has_text='Metric').click()
    page.get_by_role('option', name='avg').click()
    drawer.get_by_role('button', name='Apply').click()

    expect(drawer).not_to_be_visible()
    avg = widget(page, 'Revenue Avg')
    expect(avg.get_by_text('1,105')).to_be_visible()
    expect(avg.get_by_text('avg of revenue')).to_be_visible()


def test_save_layout_does_not_persist_rendered_widget_data(page, data_dir):
    page.get_by_role('button', name='Save Layout').click()
    page.wait_for_timeout(700)

    with open(os.path.join(data_dir, 'projects', 'default.json')) as f:
        saved = f.read()

    assert 'Bound Regions Table' in saved
    assert 'Sales Pie' in saved
    assert 'Revenue Avg' in saved
    assert '"columns"' not in saved
    assert '"rows"' not in saved
    assert '"data_error"' not in saved
    assert '"chart":' not in saved
    assert '"kpi":' not in saved
