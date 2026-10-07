"""Test for ETL Editor page and FlowEditor Vue component."""

import json
import os
import time
import socket
import tempfile
import subprocess
import urllib.request
from playwright.sync_api import sync_playwright

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def etl_editor_status(port):
    """GET /etl-editor and return its HTTP status code."""
    req = urllib.request.Request(f'http://127.0.0.1:{port}/etl-editor', headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req).status

def test_etl_editor_page():
    port = get_free_port()
    env = os.environ.copy()
    env['NICEGUI_SCREEN_TEST_PORT'] = str(port)
    # Isolate storage: the developer machine may hold projects with an empty pipeline.
    env['DATA_DIR'] = tempfile.mkdtemp()
    log_f = tempfile.NamedTemporaryFile(mode='w+', delete=False)
    proc = subprocess.Popen(['python3', '-m', 'pybi.main', '--port', str(port)], env=env, stdout=log_f, stderr=log_f)
    try:
        server_ready = False
        req = urllib.request.Request(f'http://127.0.0.1:{port}/etl-editor', headers={'User-Agent': 'Mozilla/5.0'})
        for _ in range(30):
            try:
                res = urllib.request.urlopen(req)
                if res.status == 200:
                    server_ready = True
                    break
            except Exception:
                time.sleep(0.5)

        if not server_ready:
            with open(log_f.name, 'r') as f:
                print(f"Server Log: {f.read()}")

        assert server_ready, "Server failed to start within timeout"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.on("console", lambda msg: print(f"BROWSER CONSOLE [{msg.type}]: {msg.text}"))
            page.on("pageerror", lambda err: print(f"BROWSER UNCAUGHT EXCEPTION: {err}"))

            page.goto(f'http://127.0.0.1:{port}/etl-editor')
            page.wait_for_selector('.flow-editor-container', timeout=10000)

            # Wait for nodes to be rendered
            page.wait_for_selector('.vue-flow__node', timeout=15000)

            nodes = page.query_selector_all('.vue-flow__node')
            print(f"Found {len(nodes)} Vue Flow nodes rendered on canvas.")
            assert len(nodes) >= 3, f"Expected at least 3 nodes, found {len(nodes)}"

            content = page.content()
            assert 'CSV Source' in content
            assert 'Filter Rows' in content
            assert 'DuckDB Table' in content

            browser.close()
            print("ETL Editor test passed successfully!")

    finally:
        proc.terminate()
        proc.wait()

def test_etl_editor_renders_project_data_files():
    """The project data file list must not break the page.

    Rendering the per-file delete button used to pass flat=True and size='sm'
    to ui.button (they are Quasar props, not constructor arguments), which
    raised TypeError -> HTTP 500 on /etl-editor -> NiceGUI reload loop.
    """
    data_dir = tempfile.mkdtemp()
    project_dir = os.path.join(data_dir, 'projects', 'demo')
    os.makedirs(os.path.join(project_dir, 'data'), exist_ok=True)
    with open(os.path.join(data_dir, 'projects', 'demo.json'), 'w', encoding='utf-8') as fh:
        json.dump({'project_id': 'demo', 'name': 'demo',
                   'etl_dag': {'nodes': [], 'edges': []},
                   'dashboard_layout': []}, fh)
    with open(os.path.join(project_dir, 'data', 'sales.csv'), 'w', encoding='utf-8') as fh:
        fh.write('region,sales\nEU,100\n')

    port = get_free_port()
    env = os.environ.copy()
    env['NICEGUI_SCREEN_TEST_PORT'] = str(port)
    env['DATA_DIR'] = data_dir
    log_f = tempfile.NamedTemporaryFile(mode='w+', delete=False)
    proc = subprocess.Popen(['python3', '-m', 'pybi.main', '--port', str(port)], env=env, stdout=log_f, stderr=log_f)
    try:
        status = None
        for _ in range(30):
            try:
                status = etl_editor_status(port)
                if status == 200:
                    break
            except Exception:
                status = None
            time.sleep(0.5)

        if status != 200:
            with open(log_f.name) as fh:
                log = fh.read()
            assert status == 200, f'/etl-editor returned {status}. Server log:\n{log}'

        html = urllib.request.urlopen(
            urllib.request.Request(f'http://127.0.0.1:{port}/etl-editor', headers={'User-Agent': 'Mozilla/5.0'})
        ).read().decode('utf-8')
        assert 'sales.csv' in html, 'The project data file was not rendered in the file list.'
    finally:
        proc.terminate()
        proc.wait()


if __name__ == '__main__':
    test_etl_editor_page()
