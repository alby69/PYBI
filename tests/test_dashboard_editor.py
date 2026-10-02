"""Test for Dashboard Editor page and DashboardGrid component."""

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

def test_dashboard_editor_page():
    port = get_free_port()
    env = os.environ.copy()
    env['NICEGUI_SCREEN_TEST_PORT'] = str(port)
    log_f = tempfile.NamedTemporaryFile(mode='w+', delete=False)
    proc = subprocess.Popen(['python3', '-m', 'pybi.main', '--port', str(port)], env=env, stdout=log_f, stderr=log_f)
    try:
        server_ready = False
        req = urllib.request.Request(f'http://127.0.0.1:{port}/dashboard-editor', headers={'User-Agent': 'Mozilla/5.0'})
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

            page.goto(f'http://127.0.0.1:{port}/dashboard-editor')
            page.wait_for_selector('.dashboard-grid-container', timeout=10000)

            # Wait for grid items to be rendered
            page.wait_for_selector('.vgl-item', timeout=15000)

            items = page.query_selector_all('.vgl-item')
            print(f"Found {len(items)} Grid items rendered on canvas.")
            assert len(items) >= 3, f"Expected at least 3 grid items, found {len(items)}"

            content = page.content()
            assert 'Quarterly Revenue' in content
            assert 'Regional Sales Bar Chart' in content
            assert 'Top Performing Regions' in content

            browser.close()
            print("Dashboard Editor test passed successfully!")

    finally:
        proc.terminate()
        proc.wait()

if __name__ == '__main__':
    test_dashboard_editor_page()
