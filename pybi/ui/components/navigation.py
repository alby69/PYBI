"""Reusable top navigation bar component for PyBI pages (DRY principle)."""

from nicegui import ui
from pybi.ui.shortcuts import render_shortcuts_help_button
from pybi.ui.theme import default_theme


def render_navigation_bar(page_title: str, current_page: str = '/'):
    """Render a consistent header bar with title, page navigation links, home button, and utilities."""
    with ui.row().classes('w-full items-center justify-between border-b pb-3 q-mb-md bg-white dark:bg-gray-800 px-4 py-2 rounded-lg shadow-sm'):
        with ui.row().classes('items-center gap-3'):
            ui.button(icon='home', on_click=lambda: ui.navigate.to('/')).props('flat round color=primary').tooltip('Return to Home')
            ui.label(page_title).classes('text-xl font-bold text-gray-900 dark:text-gray-100')

        with ui.row().classes('items-center gap-2'):
            if current_page != '/etl-editor':
                ui.button('ETL Editor', icon='account_tree', on_click=lambda: ui.navigate.to('/etl-editor')).props('flat size=sm color=primary')
            if current_page != '/dashboard-editor':
                ui.button('Dashboard Editor', icon='dashboard', on_click=lambda: ui.navigate.to('/dashboard-editor')).props('flat size=sm color=secondary')
            if current_page != '/viewer':
                ui.button('Viewer', icon='visibility', on_click=lambda: ui.navigate.to('/viewer')).props('flat size=sm color=positive')

            ui.separator().props('vertical').classes('mx-1')
            render_shortcuts_help_button()
            default_theme.render_toggle_button()
