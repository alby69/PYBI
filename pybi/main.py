"""Main UI entry point and page routes for PyBI."""

from nicegui import ui
import click
from fastapi import Request

from pybi.ui.components.navbar import render_navbar


def setup_routes():
    @ui.page('/')
    def home_page():
        from pybi.ui.onboarding import WelcomeWizard
        wizard = WelcomeWizard()

        render_navbar(active='/')

        with ui.row().classes('w-full justify-between items-center q-mb-md q-mt-md'):
            ui.label('Welcome to OpenBI / PyBI').classes('text-2xl font-bold')
            wizard.render_button()

        ui.label('Python Business Intelligence Platform - Power BI Style Workspace').classes('text-gray-600 q-mb-lg')

        with ui.row().classes('gap-4 flex-wrap'):
            ui.button('Welcome Tour', on_click=wizard.open).props('outline color=info icon=auto_awesome')

    @ui.page('/etl-editor')
    def etl_editor_page():
        ui.navigate.to('/power-query')

    @ui.page('/power-query')
    def power_query_page():
        from pybi.ui.pages.power_query import create_power_query_page
        create_power_query_page()

    @ui.page('/model-editor')
    def model_editor_page():
        from pybi.ui.pages.model_editor import create_model_editor_page
        create_model_editor_page()

    @ui.page('/dashboard-editor')
    def dashboard_editor_page():
        from pybi.ui.pages.dashboard_editor import create_dashboard_editor_page
        create_dashboard_editor_page()

    @ui.page('/viewer')
    def viewer_page(request: Request):
        from pybi.ui.pages.viewer import create_viewer_page
        create_viewer_page(initial_project=str(request.query_params.get('project', '')))

@click.command()
@click.option('--port', default=8080, help='Port to run NiceGUI server on')
@click.option('--host', default='0.0.0.0', help='Host to bind NiceGUI server to')
def cli(port: int, host: str):
    setup_routes()

    # Serve the REST API from the same app instead of mounting a sub-application:
    # a mount at '' would shadow NiceGUI's runtime-registered routes (e.g. uploads).
    from nicegui import app as nicegui_app
    from pybi.api.main import register_routers
    register_routers(nicegui_app)

    ui.run(title='PyBI - OpenBI Platform', host=host, port=port, reload=False, show=False)

if __name__ in {"__main__", "__mp_main__"}:
    cli()
