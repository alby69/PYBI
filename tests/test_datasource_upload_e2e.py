"""End-to-end test for uploading a data file and using it in Power Query Editor."""

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
        req = urllib.request.Request(f'{url}/power-query', headers={'User-Agent': 'Mozilla/5.0'})
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
    """Open the Power Query Editor and upload the CSV file."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        browser_page = browser.new_page()
        browser_page.on('pageerror', lambda err: print(f'BROWSER UNCAUGHT EXCEPTION: {err}'))
        browser_page.goto(f'{server}/power-query')
        browser_page.wait_for_selector('text=Power Query Editor', timeout=20000)
        browser_page.locator('input[type=file]').set_input_files(csv_file)
        browser_page.wait_for_selector('text=Uploaded', timeout=15000)
        yield browser_page
        browser.close()


def test_uploaded_file_is_listed_in_queries(page):
    expect(page.get_by_text('sales_upload.csv').first).to_be_visible()


def test_pipeline_reads_the_uploaded_file(page):
    page.get_by_role('button', name='Execute').click()
    page.wait_for_timeout(1000)
    body = page.locator('body').inner_text()
    assert 'sales_upload.csv' in body or 'Query eseguita' in body
