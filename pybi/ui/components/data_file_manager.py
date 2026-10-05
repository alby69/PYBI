"""Data manager component for uploading and listing project data files."""

from nicegui import ui
from pybi.core.storage import default_storage


class DataFileManager:
    """Drawer/dialog manager for project data source file uploads."""

    def __init__(self, get_project_id, on_upload_complete=None):
        self.get_project_id = get_project_id
        self.on_upload_complete = on_upload_complete
        self.dialog = ui.dialog()

    def open(self):
        """Open data files management dialog."""
        self._render()
        self.dialog.open()

    def _render(self):
        self.dialog.clear()
        project_id = self.get_project_id()
        files = default_storage.list_project_data_files(project_id)

        with self.dialog, ui.card().classes('w-[500px] p-4 gap-3'):
            ui.label(f'Project Data Files ({project_id})').classes('text-lg font-bold mb-1')
            ui.label('Upload local CSV, Parquet, or SQLite files into the project data directory.').classes('text-xs text-gray-500 mb-2')

            def handle_upload(e):
                filename = e.name
                content = e.content.read()
                dest = default_storage.save_project_data_file(project_id, filename, content)
                ui.notify(f'Uploaded "{filename}" to project data folder', type='positive')
                self._render()
                if self.on_upload_complete:
                    self.on_upload_complete(filename, dest)

            ui.upload(
                label='Upload File (CSV, Parquet, SQLite)',
                on_upload=handle_upload,
                auto_upload=True
            ).classes('w-full mb-3')

            ui.label('Files in Project Data Directory:').classes('text-xs font-semibold text-gray-700')
            with ui.column().classes('w-full max-h-40 overflow-y-auto gap-1 border p-2 rounded bg-gray-50'):
                if files:
                    for f in files:
                        with ui.row().classes('w-full justify-between items-center text-xs py-1 px-2 bg-white rounded shadow-xs'):
                            ui.label(f'📄 {f}').classes('font-mono')
                else:
                    ui.label('No files uploaded yet in data folder.').classes('text-xs text-gray-400 italic')

            ui.button('Close', on_click=self.dialog.close).props('flat dense').classes('mt-2 align-self-end')

    def render_button(self):
        """Render a button to launch the data file manager."""
        btn = ui.button('Upload Data', icon='upload_file', on_click=self.open).props('color=info icon=upload_file')
        return btn
