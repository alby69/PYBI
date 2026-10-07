"""Shared top navigation bar for all PyBI pages."""

from nicegui import ui

NAV_ITEMS = [
    ('Home', '/'),
    ('ETL Editor', '/etl-editor'),
    ('Dashboard Editor', '/dashboard-editor'),
    ('Public Viewer', '/viewer'),
]


def render_navbar(active: str = '') -> None:
    """Render the consistent top navigation bar.

    Args:
        active: Route of the currently active page (e.g. '/viewer') to highlight.
    """
    with ui.header().classes('bg-blue-700 text-white shadow-md'):
        with ui.row().classes('w-full items-center gap-4 px-4 py-2'):
            ui.label('PyBI').classes('text-xl font-bold mr-2')
            for label, path in NAV_ITEMS:
                style = 'font-bold underline underline-offset-4' if path == active else 'text-blue-100 hover:text-white'
                ui.link(label, path).classes(f'no-underline {style}')
            ui.space()