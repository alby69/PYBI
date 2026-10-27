"""End-to-end test for the Power Query ETL Editor actions, steps, and project manager."""

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
    """Start the PyBI server in a subprocess with isolated storage and yield its base URL."""
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
        browser_page.wait_for_selector('text=Power Query Editor', timeout=20000)
        yield browser_page
        browser.close()


def selected_project(page):
    """Read the project id currently shown in the project selector."""
    return page.locator('.q-select', has_text='Project').locator('input').input_value()


def choose_project(page, project_id):
    """Switch to another project through the project selector."""
    page.locator('.q-select').first.click()
    page.get_by_role('option', name=project_id).click()
    page.wait_for_timeout(700)


def test_quick_actions_bar_shows_buttons(page):
    for label in ('Filtra Righe', 'Rinomina Colonna', 'Modifica Tipo', 'Rimuovi Colonna', 'Aggiungi Colonna'):
        expect(page.get_by_role('button', name=label)).to_be_visible()


def test_applied_steps_panel_renders(page):
    expect(page.get_by_text('Passaggi Applicati')).to_be_visible()
    expect(page.get_by_text('Origine Dati').first).to_be_visible()


def test_add_filter_step(page):
    page.get_by_role('button', name='Filtra Righe').click()
    dialog = page.locator('.q-dialog').filter(has_text='Filtra Righe')
    expect(dialog).to_be_visible()

    dialog.get_by_label('Valore').fill('EU')
    dialog.get_by_role('button', name='Applica').click()
    expect(dialog).not_to_be_visible()

    expect(page.get_by_text('Filtra', exact=False).first).to_be_visible()


def test_saved_pipeline_is_restored_after_reload(page):
    page.get_by_role('button', name='Salva Query').click()
    page.wait_for_timeout(600)

    page.reload()
    page.wait_for_selector('text=Power Query Editor', timeout=20000)
    expect(page.get_by_text('Filtra', exact=False).first).to_be_visible()


def test_switching_projects_loads_their_own_pipeline(page):
    page.get_by_role('button', name='Create a new project').click()
    create_dialog = page.locator('.q-dialog').filter(has_text='New Project')
    create_dialog.get_by_label('Project ID').fill('e2e_copy')
    create_dialog.get_by_role('button', name='Create').click()
    expect(create_dialog).not_to_be_visible()

    page.get_by_role('button', name='Salva Query').click()
    page.wait_for_timeout(600)

    choose_project(page, 'default')
    expect(page.get_by_text('Filtra', exact=False).first).to_be_visible()

    choose_project(page, 'e2e_copy')


def test_rename_project_preserves_pipeline(page):
    choose_project(page, 'default')

    page.get_by_role('button', name='Rename the current project').click()
    rename_dialog = page.locator('.q-dialog').filter(has_text='Rename Project')
    expect(rename_dialog).to_be_visible()
    rename_dialog.get_by_label('New project ID').fill('e2e_renamed')
    rename_dialog.get_by_role('button', name='Rename').click()
    expect(rename_dialog).not_to_be_visible()

    assert 'e2e_renamed' in selected_project(page)


def test_delete_project(page):
    page.get_by_role('button', name='Delete the current project').click()
    delete_dialog = page.locator('.q-dialog').filter(has_text='Delete Project')
    expect(delete_dialog).to_be_visible()
    delete_dialog.get_by_role('button', name='Delete').click()
    expect(delete_dialog).not_to_be_visible()
    assert 'e2e_renamed' not in selected_project(page)
