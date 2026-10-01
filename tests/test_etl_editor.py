"""Test for ETL Editor page and FlowEditor Vue component."""

import time
import subprocess
import urllib.request
from playwright.sync_api import sync_playwright

def test_etl_editor_page():
    proc = subprocess.Popen(['python3', '-m', 'pybi.main'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        server_ready = False
        for _ in range(30):
            try:
                res = urllib.request.urlopen('http://127.0.0.1:8080/etl-editor')
                if res.status == 200:
                    server_ready = True
                    break
            except Exception:
                time.sleep(0.5)

        assert server_ready, "Server failed to start within timeout"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.on("console", lambda msg: print(f"BROWSER CONSOLE [{msg.type}]: {msg.text}"))
            page.on("pageerror", lambda err: print(f"BROWSER UNCAUGHT EXCEPTION: {err}"))

            page.goto('http://127.0.0.1:8080/etl-editor')
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

if __name__ == '__main__':
    test_etl_editor_page()
