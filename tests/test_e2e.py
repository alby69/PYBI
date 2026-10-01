"""End-to-End Playwright test suite for Phase 0 OpenBI/PyBI platform."""

import os
import time
import subprocess
import urllib.request
from playwright.sync_api import sync_playwright

def run_e2e_tests():
    os.makedirs('screenshots', exist_ok=True)

    proc = subprocess.Popen(['python3', '-m', 'pybi.main'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        server_ready = False
        for _ in range(30):
            try:
                res = urllib.request.urlopen('http://127.0.0.1:8080/')
                if res.status == 200:
                    server_ready = True
                    break
            except Exception:
                time.sleep(0.5)

        assert server_ready, "Server failed to start within timeout"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # 1. Test Home Page
            print("Testing Home Page (/)...")
            page.goto('http://127.0.0.1:8080/')
            page.wait_for_selector('text=Welcome to OpenBI / PyBI', timeout=5000)
            page.screenshot(path='screenshots/home_page.png')

            # 2. Test ETL Editor Page
            print("Testing ETL Editor Page (/etl-editor)...")
            page.goto('http://127.0.0.1:8080/etl-editor')
            page.wait_for_selector('.vue-flow__node', timeout=15000)
            nodes = page.query_selector_all('.vue-flow__node')
            assert len(nodes) >= 3, f"Expected 3 Vue Flow nodes, found {len(nodes)}"
            page.screenshot(path='screenshots/etl_editor_page.png')

            # 3. Test Dashboard Editor Page
            print("Testing Dashboard Editor Page (/dashboard-editor)...")
            page.goto('http://127.0.0.1:8080/dashboard-editor')
            page.wait_for_selector('.vgl-item', timeout=15000)
            items = page.query_selector_all('.vgl-item')
            assert len(items) >= 3, f"Expected at least 3 grid items, found {len(items)}"
            page.screenshot(path='screenshots/dashboard_editor_page.png')

            # 4. Test Public Viewer Page
            print("Testing Public Viewer Page (/viewer)...")
            page.goto('http://127.0.0.1:8080/viewer')
            page.wait_for_selector('.vgl-item', timeout=15000)
            items = page.query_selector_all('.vgl-item')
            assert len(items) >= 3, f"Expected at least 3 read-only items, found {len(items)}"
            # Verify read-only mode by checking absence of edit coordinates footer
            content = page.content()
            assert 'READ ONLY' in content
            assert 'Executive Sales Dashboard' in content
            page.screenshot(path='screenshots/viewer_page.png')

            browser.close()
            print("All End-to-End tests passed successfully!")

    finally:
        proc.terminate()
        proc.wait()

if __name__ == '__main__':
    run_e2e_tests()
