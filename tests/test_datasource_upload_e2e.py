"""End-to-end test for uploading a data file and using it in a Data Source node."""

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
def server():
    """Start the PyBI server in a subprocess with isolated storage and yield its base URL."""
    port = get_free_port()
    data_dir = tempfile.mkdtemp()
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
        req = urllib.request.Request(f'{url}/etl-editor', headers={'User-Agent': 'Mozilla/5.0'})
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
def csv_file():
    """A CSV file that looks like it came from the user's computer."""
    path = os.path.join(tempfile.mkdtemp(), 'sales_upload.csv')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('region,revenue,units\nEU,100,10\nUS,200,20\nAPAC,300,30\n')
    return path


@pytest.fixture(scope='module')
def page(server, csv_file):
    """Open the ETL Editor and upload the CSV file."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        browser_page = browser.new_page()
        browser_page.on('pageerror', lambda err: print(f'BROWSER UNCAUGHT EXCEPTION: {err}'))
        browser_page.goto(f'{server}/etl-editor')
        browser_page.wait_for_selector('.vue-flow__node', timeout=20000)
        browser_page.locator('input[type=file]').set_input_files(csv_file)
        browser_page.wait_for_selector('text=salvato in', timeout=15000)
        yield browser_page
        browser.close()


def property_panel(page, marker):
    """Locate the right drawer property panel whose form contains the given marker."""
    return page.locator('.q-drawer', has_text=marker)


def test_uploaded_file_is_offered_in_data_source_dropdown(page):
    page.locator('.vue-flow__node', has_text='CSV Source').dblclick()

    panel = property_panel(page, 'Data file')
    expect(panel).to_be_visible()

    data_file_select = panel.locator('.q-select', has_text='Data file').first
    data_file_select.click()
    expect(page.get_by_role('option', name='sales_upload.csv')).to_be_visible()

    page.get_by_role('option', name='sales_upload.csv').click()
    panel.get_by_role('button', name='Apply').click()
    expect(panel).not_to_be_visible()
    expect(page.locator('.vue-flow__node', has_text='sales_upload.csv')).to_be_visible()


def test_pipeline_reads_the_uploaded_file(page):
    page.get_by_role('button', name='Execute Pipeline').click()
    page.wait_for_selector('text=Output Table: filtered_sales', timeout=15000)

    log_text = page.locator('.nicegui-log').inner_text()
    assert 'sales_upload.csv' in log_text
    assert 'projects/default/data' in log_text
    expect(page.get_by_text('Execution Succeeded')).to_be_visible()
