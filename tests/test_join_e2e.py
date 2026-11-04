"""End-to-end test for Power Query Editor page execution."""

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
        req = urllib.request.Request(f'{url}/power-query', headers={'User-Agent': 'Mozilla/5.0'})
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
    """Open the Power Query editor in a headless browser."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        browser_page = browser.new_page()
        browser_page.goto(f'{server}/power-query')
        browser_page.wait_for_selector('text=Power Query Editor', timeout=20000)
        yield browser_page
        browser.close()


def test_power_query_editor_loads(page):
    """Power Query Editor renders successfully with ribbon buttons and applied steps."""
    expect(page.get_by_text('Power Query Editor').first).to_be_visible()
    expect(page.get_by_text('Query Settings').first).to_be_visible()
    expect(page.get_by_role('button', name='Execute')).to_be_visible()


def test_get_data_opens_upload_file_chooser(page):
    with page.expect_file_chooser():
        page.get_by_role('button', name='Get Data').click()


def test_query_panel_commands(page):
    page.once('dialog', lambda dialog: dialog.accept('E2E Query'))
    page.get_by_role('button', name='New Query').click()
    query_row = page.locator('.queries-pane .group.relative').filter(has_text='E2E Query').first
    expect(query_row).to_be_visible()
    query_row.click()
    expect(page.get_by_text('Active Table: E2E Query')).to_be_visible()

    query_row.locator('button[title="Query actions"]').click()
    page.get_by_text('📋 Duplicate', exact=True).click()
    duplicate_row = page.locator('.queries-pane .group.relative').filter(has_text='E2E Query_copy').first
    expect(duplicate_row).to_be_visible()

    query_row.locator('button[title="Query actions"]').click()
    page.get_by_text('🔗 Reference', exact=True).click()
    reference_row = page.locator('.queries-pane .group.relative').filter(has_text='E2E Query_ref').first
    expect(reference_row).to_be_visible()

    query_row.locator('button[title="Query actions"]').click()
    page.once('dialog', lambda dialog: dialog.accept('Renamed Query'))
    page.get_by_text('✏️ Rename', exact=True).click()
    renamed_row = page.locator('.queries-pane .group.relative').filter(has_text='Renamed Query').first
    expect(renamed_row).to_be_visible()
    expect(page.get_by_text('Query renamed to "Renamed Query".')).to_be_visible()

    renamed_row.locator('button[title="Query actions"]').click()
    page.once('dialog', lambda dialog: dialog.accept('Archive'))
    page.get_by_text('📁 Move to Group', exact=True).click()
    expect(page.get_by_text('📁 Archive')).to_be_visible()
    expect(page.get_by_text('Query "Renamed Query" moved to group "Archive".')).to_be_visible()

    page.locator('.queries-pane input').fill('E2E Query_ref')
    expect(reference_row).to_be_visible()
    expect(renamed_row).not_to_be_visible()
    page.locator('.queries-pane input').fill('')

    renamed_row.locator('button[title="Query actions"]').click()
    page.once('dialog', lambda dialog: dialog.accept())
    page.get_by_text('🗑️ Delete', exact=True).click()
    expect(renamed_row).not_to_be_visible()


def test_model_editor_can_remove_selected_table(page, server):
    page.goto(f'{server}/model-editor')
    page.get_by_text('Model View - Visual Table & Relationship Editor').wait_for()
    bindings = page.locator('.vue-flow__edge-path').evaluate_all("edges => edges.map(edge => { const hasHandle = (node, id) => [...document.querySelectorAll('.vue-flow__handle')].some(handle => handle.dataset.nodeid === node && handle.dataset.handleid === id); const source = edge.getAttribute('source'); const target = edge.getAttribute('target'); const sourceHandle = edge.getAttribute('sourceHandleId'); const targetHandle = edge.getAttribute('targetHandleId'); return { sourceAttached: hasHandle(source, sourceHandle), targetAttached: hasHandle(target, targetHandle) }; })")
    assert bindings and all(edge['sourceAttached'] and edge['targetAttached'] for edge in bindings)
    table_node = page.locator('.vue-flow__node').filter(has_text='sales').first
    expect(table_node).to_be_visible(timeout=20000)
    table_node.click()
    expect(page.get_by_text('Proprietà Tabella')).to_be_visible()

    stores_node = page.locator('.vue-flow__node').filter(has_text='stores').first
    expect(stores_node).to_be_visible()
    box = stores_node.bounding_box()
    page.mouse.move(box['x'] + 100, box['y'] + 12)
    page.mouse.down()
    page.mouse.move(box['x'] + 220, box['y'] + 112, steps=8)
    page.mouse.up()
    expect(page.get_by_text('State: Position saved for "stores"')).to_be_visible(timeout=5000)
    page.reload()
    page.get_by_text('Model View - Visual Table & Relationship Editor').wait_for()
    expect(page.locator('.vue-flow__node').filter(has_text='stores')).to_be_visible()

    table_node = page.locator('.vue-flow__node').filter(has_text='sales').first
    table_node.click()
    page.get_by_role('button', name='Rimuovi tabella dal modello').click()
    expect(page.locator('.vue-flow__node').filter(has_text='sales')).to_have_count(0)
    expect(page.locator('.vue-flow__edge')).to_have_count(0)
    expect(page.get_by_text('Tabella "sales" rimossa dal modello')).to_be_visible()
    page.reload()
    page.get_by_text('Model View - Visual Table & Relationship Editor').wait_for()
    expect(page.locator('.vue-flow__node').filter(has_text='sales')).to_have_count(0)
    stores_node = page.locator('.vue-flow__node').filter(has_text='stores').first
    expect(stores_node).to_be_visible()
    stores_node.click()
    page.get_by_role('button', name='Rimuovi tabella dal modello').click()
    expect(page.locator('.vue-flow__node')).to_have_count(0)
    page.reload()
    page.get_by_text('Model View - Visual Table & Relationship Editor').wait_for()
    expect(page.locator('.vue-flow__node')).to_have_count(0)


def test_model_editor_relationship_columns_follow_selected_table(page, server):
    page.goto(f'{server}/model-editor')
    page.get_by_text('Model View - Visual Table & Relationship Editor').wait_for()
    page.get_by_role('button', name='Generate from Schema').click()
    page.locator('.vue-flow__edge-path').first.wait_for()
    page.locator('.vue-flow__edge-path').first.click()

    from_table = page.get_by_role('combobox', name='Tabella di Origine (From Table)')
    from_column = page.get_by_role('combobox', name='Campo di Origine (From Column)')
    from_table.click()
    page.get_by_role('option', name='stores', exact=True).click()
    expect(page.locator('.vue-flow__edge-path').first).to_have_attribute('source', 'stores')
    from_column.click()
    from_columns_menu = page.locator('.q-menu').last
    expect(from_columns_menu).to_contain_text('store_name')
    expect(from_columns_menu).to_contain_text('country')
    page.get_by_role('option', name='store_name', exact=True).click()
    expect(page.locator('.vue-flow__edge-path').first).to_have_attribute('sourceHandleId', 'source:store_name')

    to_table = page.get_by_role('combobox', name='Tabella di Destinazione (To Table)')
    to_column = page.get_by_role('combobox', name='Campo di Destinazione (To Column)')
    to_table.click()
    page.get_by_role('option', name='sales', exact=True).click()
    expect(page.locator('.vue-flow__edge-path').first).to_have_attribute('target', 'sales')
    to_column.click()
    to_columns_menu = page.locator('.q-menu').last
    expect(to_columns_menu).to_contain_text('region')
    page.get_by_role('option', name='sale_id', exact=True).click()
    expect(page.locator('.vue-flow__edge-path').first).to_have_attribute('targetHandleId', 'target:sale_id')


def test_model_editor_relationships_delete_from_manager_and_properties(page, server):
    page.goto(f'{server}/model-editor')
    page.get_by_text('Model View - Visual Table & Relationship Editor').wait_for()
    page.get_by_role('button', name='Generate from Schema').click()
    edge = page.locator('.vue-flow__edge-path').first
    expect(edge).to_be_visible()
    initial_count = page.locator('.vue-flow__edge-path').count()

    page.get_by_role('button', name='Gestisci relazioni').click()
    expect(page.get_by_text('sales.store_id  →  stores.store_id')).to_be_visible()
    page.locator('.relationship-entry').first.get_by_role('button', name='Elimina', exact=True).click()
    expect(page.locator('.vue-flow__edge-path')).to_have_count(initial_count - 1)
    page.reload()
    page.get_by_text('Model View - Visual Table & Relationship Editor').wait_for()
    expect(page.locator('.vue-flow__edge-path')).to_have_count(initial_count - 1)

    page.get_by_role('button', name='Generate from Schema').click()
    edge = page.locator('.vue-flow__edge-path').first
    expect(edge).to_be_visible()
    sidebar_count = page.locator('.vue-flow__edge-path').count()
    edge.click()
    page.get_by_role('button', name='Elimina Relazione').click()
    expect(page.locator('.vue-flow__edge-path')).to_have_count(sidebar_count - 1)
    page.reload()
    page.get_by_text('Model View - Visual Table & Relationship Editor').wait_for()
    expect(page.locator('.vue-flow__edge-path')).to_have_count(sidebar_count - 1)


def test_model_editor_can_create_relationship_and_clear_properties(page, server):
    page.goto(f'{server}/model-editor')
    page.get_by_text('Model View - Visual Table & Relationship Editor').wait_for()
    page.get_by_role('button', name='Generate from Schema').click()
    expect(page.locator('.vue-flow__edge-path').first).to_be_visible()
    expect(page.get_by_text('Seleziona una tabella o una relazione nel canvas per visualizzarne le proprietà.')).to_be_visible()

    page.locator('.vue-flow__edge-path').first.click(force=True)
    expect(page.get_by_role('combobox', name='Tabella di Origine (From Table)')).to_be_visible()
    page.locator('.vue-flow__pane').click(position={'x': 20, 'y': 20})
    expect(page.get_by_text('Seleziona una tabella o una relazione nel canvas per visualizzarne le proprietà.')).to_be_visible()
    expect(page.get_by_role('combobox', name='Tabella di Origine (From Table)')).not_to_be_visible()

    page.get_by_role('button', name='Nuova relazione').click()
    page.get_by_role('button', name='Crea relazione').wait_for()
    from_column = page.get_by_role('combobox', name='Colonna di origine')
    from_column.click()
    page.get_by_role('option', name='region', exact=True).click()
    to_column = page.get_by_role('combobox', name='Colonna di destinazione')
    to_column.click()
    page.get_by_role('option', name='country', exact=True).click()
    page.get_by_role('button', name='Crea relazione').click()

    expect(page.locator('.vue-flow__edge-path')).to_have_count(2)
    created_edge = page.locator(
        '.vue-flow__edge-path[sourceHandleId="source:region"][targetHandleId="target:country"]'
    )
    expect(created_edge).to_have_count(1)
    attached_handles = created_edge.evaluate("""edge => {
        const source = edge.getAttribute('source');
        const target = edge.getAttribute('target');
        const sourceHandle = edge.getAttribute('sourceHandleId');
        const targetHandle = edge.getAttribute('targetHandleId');
        const handles = [...document.querySelectorAll('.vue-flow__handle')];
        return {
            sourceAttached: handles.some(handle => handle.classList.contains('source')
                && handle.dataset.nodeid === source && handle.dataset.handleid === sourceHandle),
            targetAttached: handles.some(handle => handle.classList.contains('target')
                && handle.dataset.nodeid === target && handle.dataset.handleid === targetHandle),
        };
    }""")
    assert attached_handles == {'sourceAttached': True, 'targetAttached': True}
    page.get_by_role('button', name='Gestisci relazioni').click()
    expect(page.get_by_text('sales.region  →  stores.country', exact=True)).to_be_visible()
    page.get_by_label('Chiudi').click()
    page.reload()
    page.get_by_text('Model View - Visual Table & Relationship Editor').wait_for()
    expect(page.locator('.vue-flow__edge-path')).to_have_count(2)


def test_model_editor_table_manager_opens_table_properties(page, server):
    page.goto(f'{server}/model-editor')
    page.get_by_text('Model View - Visual Table & Relationship Editor').wait_for()
    page.get_by_role('button', name='Generate from Schema').click()
    page.get_by_role('button', name='Gestisci tabelle').click()

    sales_entry = page.locator('.table-management-entry').filter(has_text='sales').first
    expect(sales_entry).to_contain_text('colonne')
    sales_entry.get_by_role('button', name='Proprietà').click()
    expect(page.get_by_text('Proprietà Tabella')).to_be_visible()
    expect(page.get_by_text('sales · sorgente:')).to_be_visible()


def test_model_editor_resizes_and_persists_table_dimensions(page, server):
    page.goto(f'{server}/model-editor')
    page.get_by_text('Model View - Visual Table & Relationship Editor').wait_for()
    table = page.locator('.vue-flow__node').filter(has_text='sales').first
    expect(table).to_be_visible()
    table.click()
    resize_handle = table.get_by_role('button', name='Ridimensiona tabella')
    expect(resize_handle).to_be_visible()

    before = table.bounding_box()
    handle = resize_handle.bounding_box()
    page.mouse.move(handle['x'] + handle['width'] / 2, handle['y'] + handle['height'] / 2)
    page.mouse.down()
    page.mouse.move(handle['x'] + handle['width'] / 2 + 100, handle['y'] + handle['height'] / 2 + 80, steps=8)
    page.mouse.up()

    expect(page.get_by_text('State: Dimensions saved for "sales"')).to_be_visible(timeout=5000)
    resized = table.bounding_box()
    assert resized['width'] > before['width'] + 50
    assert resized['height'] > before['height'] + 40
    saved_dimensions = table.evaluate("node => ({width: node.style.width, height: node.style.height})")
    assert saved_dimensions['width'] and saved_dimensions['height']

    page.reload()
    page.get_by_text('Model View - Visual Table & Relationship Editor').wait_for()
    table = page.locator('.vue-flow__node').filter(has_text='sales').first
    restored_dimensions = table.evaluate("node => ({width: node.style.width, height: node.style.height})")
    assert restored_dimensions == saved_dimensions
