"""Legacy ETL Editor redirect page."""

from nicegui import ui


def create_etl_editor_page():
    ui.navigate.to('/power-query')
