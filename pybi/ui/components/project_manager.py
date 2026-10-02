"""Reusable project selector with create, rename and delete actions."""

from typing import Callable, List, Optional

from nicegui import ui

from pybi.core.storage import FileProjectStorage, ProjectStorage, default_storage, sanitize_project_id


class ProjectManager:
    """NiceGUI widget to pick the active project and manage the project list."""

    def __init__(
        self,
        storage: Optional[ProjectStorage] = None,
        value: str = "default",
        on_switch: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        """Initialize the project manager.

        Args:
            storage: Project storage backend, defaults to the shared singleton.
            value: Initially selected project id.
            on_switch: Callback invoked as on_switch(project_id, action) after
                create, rename, delete or selection changes.
        """
        self._storage = storage or default_storage
        self._on_switch = on_switch
        self._current = sanitize_project_id(value)
        self._updating = False

        initial_options = self._storage.list_projects()
        if initial_options and self._current not in initial_options:
            self._current = initial_options[0]

        select_args = {
            'label': 'Project',
            'on_change': self._handle_select,
            'with_input': True,
        }
        if initial_options:
            select_args['value'] = self._current

        self.select = (
            ui.select(initial_options, **select_args)
            .props('dense outlined options-dense')
            .classes('w-64')
        )
        self.create_button = (
            ui.button(icon='add', on_click=self.open_create_dialog)
            .props("flat dense aria-label='Create a new project'")
            .tooltip('Create a new project')
        )
        self.rename_button = (
            ui.button(icon='edit', on_click=self.open_rename_dialog)
            .props("flat dense aria-label='Rename the current project'")
            .tooltip('Rename the current project')
        )
        self.delete_button = (
            ui.button(icon='delete', on_click=self.open_delete_dialog)
            .props("flat dense color=negative aria-label='Delete the current project'")
            .tooltip('Delete the current project')
        )
        self.refresh_button = (
            ui.button(icon='refresh', on_click=self.refresh)
            .props("flat dense aria-label='Refresh project list'")
            .tooltip('Refresh project list')
        )

        with ui.dialog() as self.create_dialog, ui.card().classes('w-96 gap-2'):
            ui.label('New Project').classes('text-lg font-bold')
            self.create_id_input = ui.input('Project ID').classes('w-full')
            self.create_name_input = ui.input('Display name (optional)').classes('w-full')
            ui.label('The ID becomes the file name in pybi_data/projects.').classes('text-xs text-gray-500')
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancel', on_click=self.create_dialog.close).props('flat')
                ui.button('Create', on_click=self._do_create).props('color=primary')

        with ui.dialog() as self.rename_dialog, ui.card().classes('w-96 gap-2'):
            ui.label('Rename Project').classes('text-lg font-bold')
            self.rename_id_input = ui.input('New project ID').classes('w-full')
            self.rename_name_input = ui.input('Display name (optional)').classes('w-full')
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancel', on_click=self.rename_dialog.close).props('flat')
                ui.button('Rename', on_click=self._do_rename).props('color=primary')

        with ui.dialog() as self.delete_dialog, ui.card().classes('w-96 gap-2'):
            ui.label('Delete Project').classes('text-lg font-bold text-red-700')
            self.delete_message = ui.label().classes('text-sm')
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancel', on_click=self.delete_dialog.close).props('flat')
                ui.button('Delete', on_click=self._do_delete).props('color=negative')

        self.refresh()

    @property
    def project_id(self) -> str:
        """Currently selected sanitized project id."""
        return self._current

    def projects(self) -> List[str]:
        """List the stored project ids."""
        return self._storage.list_projects()

    def refresh(self) -> None:
        """Reload the project list, keeping the current selection when possible."""
        options = self.projects()
        if options and self._current not in options:
            self._current = options[0]
        self._updating = True
        try:
            self.select.options = options
            self.select.update()
            if options:
                self.select.value = self._current
        finally:
            self._updating = False
        self._update_buttons()

    def open_create_dialog(self) -> None:
        """Open the create project dialog with an unused suggested id."""
        self.create_id_input.value = self._suggest_id()
        self.create_name_input.value = ''
        self.create_dialog.open()

    def open_rename_dialog(self) -> None:
        """Open the rename dialog prefilled with the current project."""
        if not self._current:
            return
        self.rename_id_input.value = self._current
        self.rename_name_input.value = ''
        self.rename_dialog.open()

    def open_delete_dialog(self) -> None:
        """Open the delete confirmation dialog for the current project."""
        if not self._current:
            return
        self.delete_message.text = (
            f'Permanently delete project "{self._current}"? Its saved pipeline and layout are removed. '
            'This cannot be undone.'
        )
        self.delete_dialog.open()

    def _suggest_id(self) -> str:
        existing = set(self.projects())
        index = 1
        while f"project_{index}" in existing:
            index += 1
        return f"project_{index}"

    def _update_buttons(self) -> None:
        has_project = bool(self._current) and self._current in set(self.projects())
        self.rename_button.set_enabled(has_project)
        self.delete_button.set_enabled(has_project)

    def _notify(self, message: str, action: str = '') -> None:
        if self._on_switch:
            self._on_switch(self._current, action)

    def _handle_select(self, e) -> None:
        if self._updating:
            return
        value = sanitize_project_id(e.value or '')
        if not value:
            return
        self._current = value
        self._update_buttons()
        self._notify('', 'select')

    def _do_create(self) -> None:
        raw_id = (self.create_id_input.value or '').strip()
        if not raw_id:
            ui.notify('Project ID is required.', type='warning')
            return
        new_id = sanitize_project_id(raw_id)
        if new_id != raw_id:
            ui.notify(f'Using "{new_id}" as project ID.', type='warning')
        if isinstance(self._storage, FileProjectStorage) and self._storage.project_exists(new_id):
            ui.notify(f'Project "{new_id}" already exists.', type='warning')
            return
        self._storage.save_project(new_id, name=(self.create_name_input.value or '').strip())
        self._current = new_id
        self.create_dialog.close()
        self.refresh()
        ui.notify(f'Created project "{new_id}"', type='positive')
        self._notify('', 'create')

    def _do_rename(self) -> None:
        raw_id = (self.rename_id_input.value or '').strip()
        if not raw_id or not self._current:
            ui.notify('Project ID is required.', type='warning')
            return
        new_id = sanitize_project_id(raw_id)
        if new_id != raw_id:
            ui.notify(f'Using "{new_id}" as project ID.', type='warning')
        try:
            result = self._storage.rename_project(
                self._current,
                new_id,
                name=(self.rename_name_input.value or '').strip() or None,
            )
        except FileNotFoundError:
            ui.notify(f'Project "{self._current}" has not been saved yet.', type='warning')
            return
        except ValueError as error:
            ui.notify(str(error), type='negative')
            return
        self._current = result
        self.rename_dialog.close()
        self.refresh()
        ui.notify(f'Renamed project to "{result}"', type='positive')
        self._notify('', 'rename')

    def _do_delete(self) -> None:
        if not self._current:
            return
        deleted = self._storage.delete_project(self._current)
        self.delete_dialog.close()
        if not deleted:
            ui.notify(f'Project "{self._current}" was not saved yet.', type='warning')
            return
        removed = self._current
        remaining = self.projects()
        self._current = remaining[0] if remaining else 'default'
        self.refresh()
        ui.notify(f'Deleted project "{removed}"', type='positive')
        self._notify('', 'delete')
