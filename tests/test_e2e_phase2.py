"""E2E test for Phase 2 data flow: CSV loading -> ETL DAG execution -> Dashboard data binding."""

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


def test_e2e_phase2_data_flow():
    port = get_free_port()
    data_dir = tempfile.mkdtemp()
    env = os.environ.copy()
    env['NICEGUI_SCREEN_TEST_PORT'] = str(port)
    env['DATA_DIR'] = data_dir
    log_f = tempfile.NamedTemporaryFile(mode='w+', delete=False)
    proc = subprocess.Popen(['python3', '-m', 'pybi.main', '--port', str(port)], env=env, stdout=log_f, stderr=log_f)
    try:
        server_ready = False
        req = urllib.request.Request(f'http://127.0.0.1:{port}/', headers={'User-Agent': 'Mozilla/5.0'})
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

            # 1. Visit ETL Editor and execute pipeline
            page.goto(f'http://127.0.0.1:{port}/etl-editor')
            page.wait_for_selector('.flow-editor-container', timeout=10000)

            # Click 'Execute Pipeline' button
            execute_btn = page.get_by_role('button', name='Execute Pipeline')
            execute_btn.click()

            # Wait for output table header or state label indicating success
            page.wait_for_selector('text=Output Table: filtered_sales', timeout=10000)
            content = page.content()
            assert 'filtered_sales' in content
            assert 'Execution Succeeded' in content or '3 rows' in content

            # 2. Navigate to Dashboard Editor and verify widgets
            page.goto(f'http://127.0.0.1:{port}/dashboard-editor')
            page.wait_for_selector('.dashboard-grid-container', timeout=10000)

            # Verify grid items and chart container are rendered
            page.wait_for_selector('.vgl-item', timeout=15000)
            items = page.query_selector_all('.vgl-item')
            assert len(items) >= 3, f"Expected at least 3 grid items, found {len(items)}"

            dashboard_content = page.content()
            assert 'Regional Sales Revenue' in dashboard_content or 'Quarterly Revenue' in dashboard_content

            browser.close()
            print("Phase 2 E2E Data Flow test passed successfully!")

    finally:
        proc.terminate()
        proc.wait()


if __name__ == '__main__':
    test_e2e_phase2_data_flow()
