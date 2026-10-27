"""End-to-end test for Power Query Editor page execution."""

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
    """Start a PyBI server with isolated storage."""
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
def page(server):
    """Open the Power Query editor in a headless browser."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        browser_page = browser.new_page()
        browser_page.goto(f'{server}/etl-editor')
        browser_page.wait_for_selector('text=Power Query Editor', timeout=20000)
        yield browser_page
        browser.close()


def test_power_query_editor_loads(page):
    """Power Query Editor renders successfully with quick action buttons and applied steps."""
    expect(page.get_by_text('Power Query Editor').first).to_be_visible()
    expect(page.get_by_text('Passaggi Applicati')).to_be_visible()
    expect(page.get_by_role('button', name='Esegui Query')).to_be_visible()
