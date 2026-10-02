"""Main UI entry point and page routes for PyBI Phase 0."""

from nicegui import ui
import click

def setup_routes():
    @ui.page('/')
    def home_page():
        ui.label('Welcome to OpenBI / PyBI').classes('text-2xl font-bold q-mb-md')
        ui.label('Python Business Intelligence Platform - Phase 0 Prototype').classes('text-gray-600 q-mb-lg')

        with ui.row().classes('gap-4'):
            ui.button('ETL Editor', on_click=lambda: ui.navigate.to('/etl-editor')).props('color=primary icon=account_tree')
            ui.button('Dashboard Editor', on_click=lambda: ui.navigate.to('/dashboard-editor')).props('color=secondary icon=dashboard')
            ui.button('Public Viewer', on_click=lambda: ui.navigate.to('/viewer')).props('color=positive icon=visibility')

    @ui.page('/etl-editor')
    def etl_editor_page():
        from pybi.ui.pages.etl_editor import create_etl_editor_page
        create_etl_editor_page()

    @ui.page('/dashboard-editor')
    def dashboard_editor_page():
        from pybi.ui.pages.dashboard_editor import create_dashboard_editor_page
        create_dashboard_editor_page()

    @ui.page('/viewer')
    def viewer_page():
        from pybi.ui.pages.viewer import create_viewer_page
        create_viewer_page()

@click.command()
@click.option('--port', default=8080, help='Port to run NiceGUI server on')
@click.option('--host', default='0.0.0.0', help='Host to bind NiceGUI server to')
def cli(port: int, host: str):
    setup_routes()
    ui.run(title='PyBI - OpenBI Platform', host=host, port=port, reload=False, show=False)

if __name__ in {"__main__", "__mp_main__"}:
    cli()
