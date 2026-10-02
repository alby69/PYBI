"""End-to-end test for the Join node in the ETL Editor palette and property editor."""

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
    """Open the ETL editor in a headless browser."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        browser_page = browser.new_page()
        browser_page.goto(f'{server}/etl-editor')
        browser_page.wait_for_selector('.vue-flow__node', timeout=20000)
        yield browser_page
        browser.close()


def open_join_dialog(page):
    """Open the Join node dialog from the palette."""
    page.get_by_role('button', name='🔗 Join Tables').first.click()
    dialog = page.locator('.q-dialog').filter(has_text='Left column')
    expect(dialog).to_be_visible()
    return dialog


def test_palette_offers_join_tables(page):
    """The Join node is listed in the palette."""
    palette = page.locator('.q-card', has_text='Add Node').first
    expect(palette.get_by_role('button', name='🔗 Join Tables')).to_be_visible()


def test_join_dialog_exposes_key_and_type_fields(page):
    """The Join dialog offers both key columns and the join type."""
    dialog = open_join_dialog(page)

    expect(dialog.get_by_label('Left column')).to_be_visible()
    expect(dialog.get_by_label('Right column')).to_be_visible()
    expect(dialog.get_by_label('Join type')).to_be_visible()

    dialog.get_by_role('button', name='Cancel').click()
    expect(dialog).not_to_be_visible()


def test_add_join_node_from_palette(page):
    """A filled Join dialog adds a node labelled with both keys and the join type."""
    before = page.locator('.vue-flow__node').count()
    dialog = open_join_dialog(page)

    dialog.get_by_label('Left column').fill('region')
    dialog.get_by_label('Right column').fill('region_code')
    dialog.get_by_label('Join type').click()
    page.get_by_role('option', name='left').click()
    dialog.get_by_role('button', name='Add Node').click()

    expect(dialog).not_to_be_visible()
    expect(page.locator('.vue-flow__node')).to_have_count(before + 1)
    expect(page.locator('.vue-flow__node', has_text='LEFT Join (region = region_code)')).to_have_count(1)


def test_join_dialog_rejects_missing_key(page):
    """A Join node without a right key cannot be created."""
    dialog = open_join_dialog(page)

    dialog.get_by_label('Left column').fill('region')
    dialog.get_by_label('Right column').fill('')
    dialog.get_by_role('button', name='Add Node').click()

    expect(dialog).to_be_visible()
    expect(page.locator('.q-notification', has_text='Right column is required')).to_be_visible()

    dialog.get_by_role('button', name='Cancel').click()
    expect(dialog).not_to_be_visible()


def test_join_node_parameters_survive_a_reload(page):
    """The Join node and its keys are persisted with the project."""
    page.get_by_role('button', name='Save Pipeline').click()
    page.wait_for_timeout(600)

    page.reload()
    page.wait_for_selector('.vue-flow__node', timeout=20000)

    expect(page.locator('.vue-flow__node', has_text='LEFT Join (region = region_code)')).to_have_count(1)