"""Shared Power BI style workspace navigation bar for all PyBI pages."""

from nicegui import ui

WORKSPACE_NAV_ITEMS = [
    ('Home', '/', 'home'),
    ('Data (ETL)', '/etl-editor', 'storage'),
    ('Model View', '/model-editor', 'account_tree'),
    ('Report (Dashboard)', '/dashboard-editor', 'dashboard'),
    ('Public Viewer', '/viewer', 'visibility'),
]


def render_navbar(active: str = '') -> None:
    """Render consistent workspace navigation bar with Power BI style icons and tabs.

    Args:
        active: Route of the currently active page (e.g. '/etl-editor') to highlight.
    """
    with ui.header().classes('bg-slate-900 text-white shadow-lg border-b border-slate-700'):
        with ui.row().classes('w-full items-center gap-2 px-4 py-2'):
            with ui.row().classes('items-center gap-2 mr-4 cursor-pointer').on('click', lambda: ui.navigate.to('/')):
                ui.icon('analytics', size='28px').classes('text-blue-400')
                ui.label('PyBI').classes('text-2xl font-black tracking-tight text-white')
                ui.label('Desktop').classes('text-xs font-semibold px-2 py-0.5 rounded bg-blue-600 text-white')

            ui.separator().props('vertical').classes('bg-slate-700 mx-2')

            # Power BI style tabs
            for label, path, icon in WORKSPACE_NAV_ITEMS:
                is_active = (path == active)
                bg_style = 'bg-blue-600 text-white font-bold shadow' if is_active else 'text-slate-300 hover:bg-slate-800 hover:text-white'
                with ui.row().classes(f'items-center gap-2 px-3 py-1.5 rounded-md cursor-pointer transition-colors {bg_style}').on('click', lambda p=path: ui.navigate.to(p)):
                    ui.icon(icon, size='20px')
                    ui.label(label).classes('text-sm font-medium')

            ui.space()
