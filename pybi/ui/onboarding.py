"""Welcome wizard for in-app onboarding."""

from typing import List, Dict, Any
from nicegui import ui


class WelcomeWizard:
    """Multi-step onboarding dialog for new users."""

    STEPS: List[Dict[str, str]] = [
        {
            'title': 'Welcome to PyBI! 🚀',
            'content': 'PyBI is a 100% Python open-source Business Intelligence platform designed as a modern alternative to PowerBI Desktop.',
            'icon': 'analytics'
        },
        {
            'title': '1. Create Your Project 📁',
            'content': 'Use the Project Manager at the top left to create or switch between project workspaces.',
            'icon': 'folder'
        },
        {
            'title': '2. Build ETL Pipelines ⚡',
            'content': 'In the ETL Editor, drag nodes onto the canvas or use the Node Palette. Double-click any node to configure parameters in the Property Panel.',
            'icon': 'account_tree'
        },
        {
            'title': '3. Design Dashboards 📊',
            'content': 'In the Dashboard Editor, drag and resize KPI, Chart, or Table widgets. Bind them reactively to DuckDB/Polars data sources.',
            'icon': 'dashboard'
        }
    ]

    def __init__(self):
        self.current_step = 0
        self.dialog = ui.dialog()

    def open(self):
        """Show onboarding wizard dialog."""
        self.current_step = 0
        self._render_step()
        self.dialog.open()

    def _render_step(self):
        self.dialog.clear()
        step = self.STEPS[self.current_step]

        with self.dialog, ui.card().classes('w-[500px] p-6 gap-4'):
            with ui.row().classes('items-center gap-3'):
                ui.icon(step['icon']).classes('text-3xl text-blue-600')
                ui.label(step['title']).classes('text-xl font-bold text-gray-800')

            ui.label(step['content']).classes('text-sm text-gray-600 leading-relaxed my-2')

            # Progress indicator dots
            with ui.row().classes('w-full justify-center gap-2 my-2'):
                for i in range(len(self.STEPS)):
                    dot_color = 'bg-blue-600' if i == self.current_step else 'bg-gray-300'
                    ui.element('div').classes(f'w-2.5 h-2.5 rounded-full {dot_color}')

            # Action buttons
            with ui.row().classes('w-full justify-between items-center mt-4'):
                if self.current_step > 0:
                    ui.button('Back', on_click=self._prev_step).props('flat dense')
                else:
                    ui.element('div')

                if self.current_step < len(self.STEPS) - 1:
                    ui.button('Next', on_click=self._next_step).props('color=primary dense')
                else:
                    ui.button('Get Started', on_click=self.dialog.close).props('color=positive dense')

    def _next_step(self):
        if self.current_step < len(self.STEPS) - 1:
            self.current_step += 1
            self._render_step()

    def _prev_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self._render_step()

    def render_button(self):
        """Render a help/welcome button."""
        btn = ui.button(icon='help_outline', on_click=self.open).props('flat dense round')
        btn.tooltip('Welcome & Onboarding Guide')
        return btn
