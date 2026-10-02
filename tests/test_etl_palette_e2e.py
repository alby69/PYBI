"""End-to-end test for the ETL Editor node palette, property editor and project manager."""

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
    """Start the PyBI server in a subprocess and yield its base URL."""
    port = get_free_port()
    env = os.environ.copy()
    env['NICEGUI_SCREEN_TEST_PORT'] = str(port)
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


def node_filter(page, text):
    """Locate a rendered Vue Flow node containing the given text."""
    return page.locator('.vue-flow__node', has_text=text)


def selected_project(page):
    """Read the project id currently shown in the project selector."""
    return page.locator('.q-select').first.locator('input').input_value()


def choose_project(page, project_id):
    """Switch to another project through the project selector."""
    page.locator('.q-select').first.click()
    page.get_by_role('option', name=project_id).click()
    page.wait_for_timeout(700)


def test_palette_shows_every_node_kind(page):
    palette = page.locator('.q-card', has_text='Add Node').first
    for label in ('Data Source', 'Filter Rows', 'Select Columns', 'Group By', 'Output Table'):
        expect(palette.get_by_role('button', name=label)).to_be_visible()


def test_sample_pipeline_renders(page):
    expect(page.locator('.vue-flow__node')).to_have_count(3)
    expect(node_filter(page, 'CSV Source')).to_have_count(1)
    expect(node_filter(page, 'DuckDB Table')).to_have_count(1)


def test_add_filter_node_from_palette(page):
    before = page.locator('.vue-flow__node').count()
    page.get_by_role('button', name='⚡ Filter Rows').first.click()

    dialog = page.locator('.q-dialog').filter(has_text='SQL condition')
    expect(dialog).to_be_visible()

    dialog.get_by_label('SQL condition').fill('sales > 300')
    dialog.get_by_role('button', name='Add Node').click()

    expect(dialog).not_to_be_visible()
    expect(page.locator('.vue-flow__node')).to_have_count(before + 1)
    expect(node_filter(page, 'sales > 300')).to_have_count(1)


def test_node_property_editor_rejects_invalid_condition(page):
    page.get_by_role('button', name='⚡ Filter Rows').first.click()
    dialog = page.locator('.q-dialog').filter(has_text='SQL condition')
    dialog.get_by_label('SQL condition').fill('')
    dialog.get_by_role('button', name='Add Node').click()
    expect(dialog).to_be_visible()
    page.get_by_role('button', name='Cancel').last.click()
    expect(dialog).not_to_be_visible()


def test_validation_blocks_disconnected_pipeline(page):
    page.get_by_role('button', name='Execute Pipeline').click()
    expect(page.get_by_text('Validation failed')).to_be_visible()


def test_saved_pipeline_is_restored_after_reload(page):
    page.get_by_role('button', name='Save Pipeline').click()
    page.wait_for_timeout(600)
    assert selected_project(page) == 'default'

    page.reload()
    page.wait_for_selector('.vue-flow__node', timeout=20000)
    expect(page.locator('.vue-flow__node')).to_have_count(4)
    expect(node_filter(page, 'sales > 300')).to_have_count(1)


def test_switching_projects_loads_their_own_pipeline(page):
    page.get_by_role('button', name='Create a new project').click()
    create_dialog = page.locator('.q-dialog').filter(has_text='New Project')
    create_dialog.get_by_label('Project ID').fill('e2e_copy')
    create_dialog.get_by_role('button', name='Create').click()
    expect(create_dialog).not_to_be_visible()
    expect(page.locator('.vue-flow__node')).to_have_count(3)

    page.get_by_role('button', name='Save Pipeline').click()
    page.wait_for_timeout(600)

    choose_project(page, 'default')
    expect(page.locator('.vue-flow__node')).to_have_count(4)
    expect(node_filter(page, 'sales > 300')).to_have_count(1)

    choose_project(page, 'e2e_copy')
    expect(page.locator('.vue-flow__node')).to_have_count(3)


def test_rename_project_preserves_pipeline(page):
    choose_project(page, 'default')

    page.get_by_role('button', name='Rename the current project').click()
    rename_dialog = page.locator('.q-dialog').filter(has_text='Rename Project')
    expect(rename_dialog).to_be_visible()
    rename_dialog.get_by_label('New project ID').fill('e2e_renamed')
    rename_dialog.get_by_role('button', name='Rename').click()
    expect(rename_dialog).not_to_be_visible()

    assert selected_project(page) == 'e2e_renamed'
    expect(page.locator('.vue-flow__node')).to_have_count(4)
    expect(node_filter(page, 'sales > 300')).to_have_count(1)


def test_delete_project(page):
    page.get_by_role('button', name='Delete the current project').click()
    delete_dialog = page.locator('.q-dialog').filter(has_text='Delete Project')
    expect(delete_dialog).to_be_visible()
    delete_dialog.get_by_role('button', name='Delete').click()
    expect(delete_dialog).not_to_be_visible()
    assert selected_project(page) != 'e2e_renamed'
