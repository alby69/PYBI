"""Test for Power Query Editor page and Vue component integration."""

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

def power_query_status(port):
    """GET /power-query and return its HTTP status code."""
    req = urllib.request.Request(f'http://127.0.0.1:{port}/power-query', headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req).status

def test_etl_editor_page():
    port = get_free_port()
    env = os.environ.copy()
    env['NICEGUI_SCREEN_TEST_PORT'] = str(port)
    env['DATA_DIR'] = tempfile.mkdtemp()
    log_f = tempfile.NamedTemporaryFile(mode='w+', delete=False)
    proc = subprocess.Popen(['python3', '-m', 'pybi.main', '--port', str(port)], env=env, stdout=log_f, stderr=log_f)
    try:
        server_ready = False
        req = urllib.request.Request(f'http://127.0.0.1:{port}/power-query', headers={'User-Agent': 'Mozilla/5.0'})
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
            page.wait_for_selector('text=Power Query Editor', timeout=10000)

            content = page.content()
            assert 'Power Query Editor' in content
            assert 'Data Preview' in content or 'Queries (' in content

            browser.close()
            print("Power Query Editor test passed successfully!")

    finally:
        proc.terminate()
        proc.wait()

def test_etl_editor_renders_project_data_files():
    """The project data file list must be rendered and managed safely."""
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
                status = power_query_status(port)
                if status == 200:
                    break
            except Exception:
                status = None
            time.sleep(0.5)

        if status != 200:
            with open(log_f.name) as fh:
                log = fh.read()
            assert status == 200, f'/power-query returned {status}. Server log:\n{log}'

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f'http://127.0.0.1:{port}/power-query')
            page.wait_for_selector('text=Power Query Editor', timeout=10000)

            # Open Manage Files dialog
            page.get_by_role('button', name='Manage Files').click()
            page.wait_for_selector('text=sales.csv', timeout=5000)

            content = page.content()
            assert 'sales.csv' in content, 'The project data file was not rendered in the file list dialog.'
            browser.close()
    finally:
        proc.terminate()
        proc.wait()


if __name__ == '__main__':
    test_etl_editor_page()
