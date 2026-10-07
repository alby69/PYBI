"""Reusable dashboard selector with create, rename and delete actions.

A project can hold multiple dashboards. This manager lists the dashboards of
the currently selected project and lets the user switch between them, create
brand new ones, rename them and delete them.
"""

from typing import Callable, Dict, List, Optional

from nicegui import ui

from pybi.core.storage import default_storage


def _next_dashboard_n(dashboards: List[str]) -> int:
    """Return the next free numeric suffix for a "Dashboard N" label."""
    used = set()
    for dash_id in dashboards:
        if dash_id.startswith('dash_') and dash_id[5:].isdigit():
            used.add(int(dash_id[5:]))
    n = 1
    while n in used:
        n += 1
    return n


class DashboardManager:
    """NiceGUI widget to pick the active dashboard and manage the dashboard list."""

    def __init__(
        self,
        project_id: str = "default",
        on_select: Optional[Callable[[Dict[str, str]], None]] = None,
        on_changed: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> None:
        """Initialize the dashboard manager.

        Args:
            project_id: Currently selected project id.
            on_select: Callback invoked as on_select({'project_id', 'dashboard_id'})
                when the user changes the selected dashboard.
            on_changed: Callback invoked as on_changed({'project_id', 'dashboard_id'})
                after create, rename or delete operations.
        """
        self.project_id = project_id
        self._on_select = on_select
        self._on_changed = on_changed
        self._current: Optional[str] = None
        self._updating = False

        self.select = (
            ui.select([], label='Dashboard', on_change=self._handle_select)
            .props('dense outlined options-dense')
            .classes('w-64')
        )
        self.add_button = (
            ui.button(icon='add', on_click=self.open_add_dialog)
            .props("flat dense aria-label='Add a new dashboard'")
            .tooltip('Add a new dashboard')
        )
        self.rename_button = (
            ui.button(icon='edit', on_click=self.open_rename_dialog)
            .props("flat dense aria-label='Rename the current dashboard'")
            .tooltip('Rename the current dashboard')
        )
        self.delete_button = (
            ui.button(icon='delete', on_click=self.open_delete_dialog)
            .props("flat dense color=negative aria-label='Delete the current dashboard'")
            .tooltip('Delete the current dashboard')
        )
        self.refresh_button = (
            ui.button(icon='refresh', on_click=self.refresh)
            .props("flat dense aria-label='Refresh dashboard list'")
            .tooltip('Refresh dashboard list')
        )

        with ui.dialog() as self.add_dialog, ui.card().classes('w-96 gap-2'):
            ui.label('New Dashboard').classes('text-lg font-bold')
            self.add_name_input = ui.input('Display name').classes('w-full')
            ui.label('The dashboard is stored inside the current project.').classes('text-xs text-gray-500')
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancel', on_click=self.add_dialog.close).props('flat')
                ui.button('Create', on_click=self._do_add).props('color=primary')

        with ui.dialog() as self.rename_dialog, ui.card().classes('w-96 gap-2'):
            ui.label('Rename Dashboard').classes('text-lg font-bold')
            self.rename_name_input = ui.input('Display name').classes('w-full')
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancel', on_click=self.rename_dialog.close).props('flat')
                ui.button('Rename', on_click=self._do_rename).props('color=primary')

        with ui.dialog() as self.delete_dialog, ui.card().classes('w-96 gap-2'):
            ui.label('Delete Dashboard').classes('text-lg font-bold text-red-700')
            self.delete_message = ui.label().classes('text-sm')
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancel', on_click=self.delete_dialog.close).props('flat')
                ui.button('Delete', on_click=self._do_delete).props('color=negative')

        self.set_project(project_id)

    @property
    def dashboard_id(self) -> Optional[str]:
        """Currently selected dashboard id, or None when no dashboard exists."""
        return self._current

    def dashboards(self) -> List[Dict[str, str]]:
        """List the dashboards of the current project."""
        if not self.project_id:
            return []
        try:
            return default_storage.list_dashboards(self.project_id)
        except Exception:
            return []

    def set_project(self, project_id: str, select_first: bool = True) -> None:
        """Switch the manager to another project and reload its dashboards.

        The caller is responsible for loading the selected dashboard's layout.
        """
        self.project_id = project_id
        self._current = None
        self._updating = True
        try:
            options = self.dashboards()
            if options:
                self._current = options[0]['id'] if select_first else self._current
            self.select.options = {d['id']: d['name'] for d in options}
            self.select.value = self._current
            self.select.update()
        finally:
            self._updating = False
        self._update_buttons()

    def refresh(self) -> None:
        """Reload the dashboard list, keeping the current selection when possible."""
        options = self.dashboards()
        if options and self._current not in {d['id'] for d in options}:
            self._current = options[0]['id']
        elif not options:
            self._current = None
        self._updating = True
        try:
            self.select.options = {d['id']: d['name'] for d in options}
            self.select.update()
            if options:
                self.select.value = self._current
        finally:
            self._updating = False
        self._update_buttons()

    def open_add_dialog(self) -> None:
        """Open the create dashboard dialog with a suggested name."""
        dash_ids = [d['id'] for d in self.dashboards()]
        self.add_name_input.value = f'Dashboard {_next_dashboard_n(dash_ids)}'
        self.add_dialog.open()

    def open_rename_dialog(self) -> None:
        """Open the rename dialog prefilled with the current dashboard name."""
        if not self._current:
            return
        name = self._current_name() or self._current
        self.rename_name_input.value = name
        self.rename_dialog.open()

    def open_delete_dialog(self) -> None:
        """Open the delete confirmation dialog for the current dashboard."""
        if not self._current:
            return
        name = self._current_name() or self._current
        self.delete_message.text = (
            f'Permanently delete dashboard "{name}" from project "{self.project_id}"? '
            'This cannot be undone.'
        )
        self.delete_dialog.open()

    def _current_name(self) -> Optional[str]:
        for dash in self.dashboards():
            if dash['id'] == self._current:
                return dash.get('name')
        return None

    def _suggest_id(self) -> str:
        used = {d['id'] for d in self.dashboards()}
        index = 1
        while f"dash_{index}" in used:
            index += 1
        return f"dash_{index}"

    def _update_buttons(self) -> None:
        has_dashboard = bool(self._current)
        self.rename_button.set_enabled(has_dashboard)
        self.delete_button.set_enabled(has_dashboard)

    def _notify_select(self) -> None:
        if self._on_select:
            self._on_select({'project_id': self.project_id, 'dashboard_id': self._current})

    def _notify_changed(self) -> None:
        if self._on_changed:
            self._on_changed({'project_id': self.project_id, 'dashboard_id': self._current})

    def _handle_select(self, e) -> None:
        if self._updating:
            return
        value = (e.value or None)
        if not value:
            return
        self._current = value
        self._update_buttons()
        self._notify_select()

    def _do_add(self) -> None:
        name = (self.add_name_input.value or '').strip() or None
        dash_id = self._suggest_id()
        default_storage.save_dashboard(self.project_id, dash_id, name or dash_id, [])
        self._current = dash_id
        self.add_dialog.close()
        self.refresh()
        ui.notify(f'Created dashboard "{dash_id}"', type='positive')
        self._notify_changed()

    def _do_rename(self) -> None:
        if not self._current:
            return
        name = (self.rename_name_input.value or '').strip()
        if not name:
            ui.notify('Dashboard name is required.', type='warning')
            return
        layout = default_storage.load_dashboard(self.project_id, self._current)
        default_storage.save_dashboard(self.project_id, self._current, name, layout or [])
        self.rename_dialog.close()
        self.refresh()
        ui.notify(f'Renamed dashboard to "{name}"', type='positive')
        self._notify_changed()

    def _do_delete(self) -> None:
        if not self._current:
            return
        removed = self._current
        deleted = default_storage.delete_dashboard(self.project_id, removed)
        self.delete_dialog.close()
        if not deleted:
            ui.notify('Dashboard could not be deleted.', type='warning')
            return
        remaining = self.dashboards()
        self._current = remaining[0]['id'] if remaining else None
        self.refresh()
        ui.notify(f'Deleted dashboard "{removed}"', type='positive')
        self._notify_changed()