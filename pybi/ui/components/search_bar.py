"""Global/page search bar component for nodes, widgets, and tables."""

from typing import Callable, List, Dict, Any
from nicegui import ui


class SearchBar:
    """Search bar component for filtering nodes, widgets, and fields."""

    def __init__(self, items_provider: Callable[[], List[Dict[str, Any]]], on_select: Callable[[Dict[str, Any]], None]):
        self.items_provider = items_provider
        self.on_select = on_select
        self.dialog = ui.dialog()

        with self.dialog, ui.card().classes('w-[500px] p-4'):
            ui.label('Search Nodes, Widgets & Tables').classes('text-lg font-bold mb-2')
            self.search_input = ui.input(
                placeholder='Type to search...',
                on_change=self._filter_results
            ).classes('w-full mb-3').props('autofocus clearable dense outlined')
            self.results_container = ui.column().classes('w-full max-h-60 overflow-y-auto gap-1')

    def open(self):
        """Open search dialog."""
        self._filter_results()
        self.dialog.open()

    def _filter_results(self, e=None):
        query = (self.search_input.value or '').strip().lower()
        items = self.items_provider()
        self.results_container.clear()

        with self.results_container:
            matched = False
            for item in items:
                title = str(item.get('title') or item.get('label') or item.get('id') or '')
                sub = str(item.get('type') or item.get('kind') or '')
                if not query or query in title.lower() or query in sub.lower():
                    matched = True
                    with ui.row().classes(
                        'w-full p-2 hover:bg-blue-50 dark:hover:bg-gray-700 cursor-pointer rounded items-center justify-between'
                    ).on('click', lambda i=item: self._select_item(i)):
                        ui.label(title).classes('text-sm font-medium')
                        ui.badge(sub, color='blue').props('dense flat')

            if not matched:
                ui.label('No matching items found').classes('text-xs text-gray-500 p-2')

    def _select_item(self, item: Dict[str, Any]):
        self.dialog.close()
        self.on_select(item)

    def render_button(self):
        """Render a search action button."""
        btn = ui.button(icon='search', on_click=self.open).props('flat dense round')
        btn.tooltip('Search (Ctrl+F)')
        return btn
