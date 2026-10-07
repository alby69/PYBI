"""End-to-end test for the Public Viewer: project + dashboard selection."""

import os
import socket
import subprocess
import tempfile
import time
import urllib.request

import pytest
from playwright.sync_api import expect, sync_playwright

from pybi.core.storage import FileProjectStorage


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@pytest.fixture(scope='module')
def data_dir():
    """Isolated DATA_DIR shared by the server fixture."""
    tmp = tempfile.mkdtemp()
    storage = FileProjectStorage(storage_dir=tmp)
    storage.save_dashboard("one_dash", "dash_1", "Sales", [
        {'i': 'k1', 'x': 0, 'y': 0, 'w': 4, 'h': 3, 'title': 'Alpha Dashboard', 'type': 'kpi', 'metric': 'sum', 'source': 'regional_sales'},
    ])
    storage.save_dashboard("two_dash", "dash_a", "Sales", [
        {'i': 'k1', 'x': 0, 'y': 0, 'w': 4, 'h': 3, 'title': 'Project Two - Sales', 'type': 'kpi', 'metric': 'sum', 'source': 'regional_sales'},
    ])
    storage.save_dashboard("two_dash", "dash_b", "Marketing", [
        {'i': 't1', 'x': 0, 'y': 0, 'w': 4, 'h': 3, 'title': 'Project Two - Marketing', 'type': 'table', 'source': 'regional_sales'},
    ])
    return tmp


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
        req = urllib.request.Request(f'{url}/viewer', headers={'User-Agent': 'Mozilla/5.0'})
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
def browser():
    """A single headless Chromium instance shared across the module's tests."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture(scope='module')
def page(server, browser):
    """Open the Public Viewer in a headless browser."""
    browser_page = browser.new_page()
    browser_page.on('pageerror', lambda err: print(f'BROWSER UNCAUGHT EXCEPTION: {err}'))
    browser_page.goto(f'{server}/viewer')
    browser_page.wait_for_selector('.vgl-item:not(.vgl-item--placeholder)', timeout=20000)
    yield browser_page
    browser_page.close()


def test_viewer_lists_projects_and_dashboards(page):
    project_select = page.locator('.q-select', has_text='Project')
    expect(project_select).to_be_visible()
    project_select.click()
    expect(page.get_by_role('option', name='one_dash')).to_be_visible()
    expect(page.get_by_role('option', name='two_dash')).to_be_visible()
    page.keyboard.press('Escape')


def test_viewer_shows_first_dashboard_by_default(page):
    expect(page.locator('.vgl-item', has_text='Alpha Dashboard')).to_be_visible()
    expect(page.get_by_text('Sales - one_dash')).to_be_visible()


def test_viewer_switches_dashboard_per_project(page):
    project_select = page.locator('.q-select', has_text='Project')
    project_select.click()
    page.get_by_role('option', name='two_dash').click()

    expect(page.locator('.vgl-item', has_text='Project Two - Sales')).to_be_visible()
    expect(page.locator('.vgl-item', has_text='Project Two - Marketing')).to_have_count(0)

    dashboard_select = page.locator('.q-select', has_text='Dashboard')
    dashboard_select.click()
    page.get_by_role('option', name='Marketing').click()

    expect(page.locator('.vgl-item', has_text='Project Two - Marketing')).to_be_visible()
    expect(page.locator('.vgl-item', has_text='Project Two - Sales')).to_have_count(0)


def test_viewer_is_read_only(page):
    expect(page.get_by_text('READ ONLY')).to_be_visible()
    items = page.locator('.vgl-item:not(.vgl-item--placeholder)')
    count = items.count()
    assert count >= 1


def test_viewer_with_project_query_param(server, browser):
    browser_page = browser.new_page()
    browser_page.on('pageerror', lambda err: print(f'BROWSER UNCAUGHT EXCEPTION: {err}'))
    browser_page.goto(f'{server}/viewer?project=two_dash')
    browser_page.wait_for_selector('.vgl-item:not(.vgl-item--placeholder)', timeout=20000)
    expect(browser_page.locator('.vgl-item', has_text='Project Two - Sales')).to_be_visible()
    browser_page.close()