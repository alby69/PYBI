"""End-to-End Playwright test suite for PYBI (OpenBI) Phase 3 platform."""

import os
import socket
import subprocess
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright


def get_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def test_e2e_full_flow():
    """Complete End-to-End test simulating ETL creation, execution and Dashboard visualization."""
    os.makedirs('screenshots', exist_ok=True)
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
                print(f"Server Log:\n{f.read()}")

        assert server_ready, "Server failed to start within timeout"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # 1. Test Home Page
            print("1. Testing Home Page (/)...")
            page.goto(f'http://127.0.0.1:{port}/')
            page.wait_for_selector('text=Welcome to OpenBI / PyBI', timeout=5000)
            page.screenshot(path='screenshots/home_page.png')

            # 2. Test ETL Editor Page & Node Flow
            print("2. Testing ETL Editor Page (/etl-editor)...")
            page.goto(f'http://127.0.0.1:{port}/etl-editor')
            page.wait_for_selector('.vue-flow__node', timeout=15000)
            nodes = page.query_selector_all('.vue-flow__node')
            assert len(nodes) >= 3, f"Expected at least 3 Vue Flow nodes, found {len(nodes)}"

            # Verify presence of CSV Source node and Filter node
            content = page.content()
            assert 'CSV Source' in content or 'sales_data.csv' in content
            assert 'Filter Rows' in content or "region = 'EU'" in content

            # Execute the pipeline
            execute_btn = page.get_by_role('button', name='Execute Pipeline')
            execute_btn.click()

            # Verify pipeline execution output
            page.wait_for_selector('text=Output Table: filtered_sales', timeout=10000)
            exec_content = page.content()
            assert 'filtered_sales' in exec_content
            assert 'Execution Succeeded' in exec_content
            page.screenshot(path='screenshots/etl_editor_executed.png')

            # 3. Test Dashboard Editor Page & Chart Visualization
            print("3. Testing Dashboard Editor Page (/dashboard-editor)...")
            page.goto(f'http://127.0.0.1:{port}/dashboard-editor')
            page.wait_for_selector('.vgl-item', timeout=15000)
            items = page.query_selector_all('.vgl-item')
            assert len(items) >= 3, f"Expected at least 3 grid items, found {len(items)}"

            # Verify dynamic chart container and data binding
            dashboard_content = page.content()
            assert 'Regional Sales Revenue' in dashboard_content or 'Dynamic Data-Bound Chart Widget' in dashboard_content
            page.screenshot(path='screenshots/dashboard_editor_page.png')

            # 4. Test Public Viewer Page
            print("4. Testing Public Viewer Page (/viewer)...")
            page.goto(f'http://127.0.0.1:{port}/viewer')
            page.wait_for_selector('.vgl-item', timeout=15000)
            items = page.query_selector_all('.vgl-item')
            assert len(items) >= 3, f"Expected at least 3 read-only items, found {len(items)}"

            viewer_content = page.content()
            assert 'READ ONLY' in viewer_content
            assert 'Executive Sales Dashboard' in viewer_content
            page.screenshot(path='screenshots/viewer_page.png')

            browser.close()
            print("All End-to-End flow tests passed successfully!")

    finally:
        proc.terminate()
        proc.wait()


if __name__ == '__main__':
    test_e2e_full_flow()
