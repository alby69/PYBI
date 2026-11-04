"""Public Viewer page implementation for read-only, project/dashboard selection using Declarative UI Schema."""

from nicegui import ui

from pybi.core.storage import default_storage
from pybi.ui.components.dashboard_grid import DashboardGrid
from pybi.ui.components.navbar import render_navbar
from pybi.ui.components.widget_data import bind_widget_data, sample_layout
from pybi.ui.shortcuts import render_shortcuts_help_button
from pybi.ui.theme import default_theme


def create_viewer_page(initial_project: str = ''):
    render_navbar(active='/viewer')

    # Big banner header, aligned with the Data (ETL) / Power Query Editor page header.
    with ui.row().classes('w-full items-end justify-between q-mt-sm'):
        with ui.column().classes('gap-0'):
            title_label = ui.label('🚀 Executive Sales Dashboard').classes('text-2xl font-bold text-slate-900')
            ui.label('Public read-only viewer mode for end-user consultation. Choose a project and dashboard to consult.').classes('text-sm text-slate-600')
        with ui.row().classes('items-center gap-2'):
            ui.chip('READ ONLY', color='positive', text_color='white', icon='lock').classes('font-bold text-xs')
            render_shortcuts_help_button()
            default_theme.render_toggle_button()

    def render_demo():
        title_label.set_text('🚀 Executive Sales Dashboard (demo)')
        grid.layout = bind_widget_data(sample_layout())

    def load_dashboard(project_id, dashboard_id):
        if not project_id:
            render_demo()
            project_select.set_value(None)
            return
        dashboards = default_storage.list_dashboards(project_id)
        labels = {d['id']: d.get('name') or d['id'] for d in dashboards}
        dashboard_select.options = labels
        if not dashboards:
            dashboard_select.set_value(None)
            render_demo()
            return
        target = dashboard_id if dashboard_id in labels else dashboards[0]['id']
        dashboard_select.set_value(target)
        layout = default_storage.load_dashboard(project_id, target)
        name = labels[target]
        title_label.set_text(f'📊 {name} - {project_id}')
        grid.layout = bind_widget_data(layout or [])

    def on_project_change(e):
        load_dashboard(e.value, None)

    def on_dashboard_change(e):
        if e.value:
            load_dashboard(project_select.value, e.value)

    with ui.row().classes('w-full items-center gap-4 q-mb-md q-mt-md'):
        project_select = (
            ui.select(default_storage.list_projects(), label='Project', with_input=True, on_change=on_project_change)
            .props('dense outlined options-dense')
            .classes('w-72')
        )
        dashboard_select = (
            ui.select([], label='Dashboard', with_input=True, on_change=on_dashboard_change)
            .props('dense outlined options-dense')
            .classes('w-64')
        )
        ui.space()

    grid = DashboardGrid(
        layout=[],
        is_draggable=False,
        is_resizable=False
    ).style('min-height: 520px; width: 100%;')

    projects = default_storage.list_projects()
    initial = initial_project if initial_project in projects else (projects[0] if projects else '')
    if initial:
        project_select.set_value(initial)
        load_dashboard(initial, None)
    else:
        render_demo()
