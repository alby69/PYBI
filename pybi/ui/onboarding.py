"""Welcome wizard and onboarding walkthrough for PyBI."""

from typing import List, Dict, Any
from nicegui import ui


class WelcomeWizard:
    """Multi-step onboarding dialog for new users."""

    STEPS: List[Dict[str, str]] = [
        {
            'title': 'Welcome to PyBI Desktop! 🚀',
            'content': 'PyBI is a 100% Python open-source Business Intelligence platform designed as a modern alternative to PowerBI Desktop.',
            'icon': 'analytics'
        },
        {
            'title': '1. Data (ETL Pipelines) 📁',
            'content': 'In Data (ETL), load raw datasets (CSV, Parquet, SQLite) and build visual transformation pipelines with Applied Steps history.',
            'icon': 'storage'
        },
        {
            'title': '2. Model View (Semantic Layer) 🔗',
            'content': 'In Model View, connect tables visually to define relationships (1:*, *:1), calculated measures, and Row-Level Security (RLS) rules.',
            'icon': 'account_tree'
        },
        {
            'title': '3. Report (Dashboard Canvas) 📊',
            'content': 'In Report, design interactive layouts with KPI cards, dynamic charts, and Excel-like Pivot Tables bound reactively to DuckDB.',
            'icon': 'dashboard'
        },
        {
            'title': '4. Secure Publish & Export 🔒',
            'content': 'In Public Viewer, share reports with active RLS filters and export high-resolution PDFs or Markdown data snapshots.',
            'icon': 'visibility'
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

        with self.dialog, ui.card().classes('w-[520px] p-6 gap-4'):
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
                    ui.button('Get Started', on_click=self._finish).props('color=positive dense')

    def _next_step(self):
        if self.current_step < len(self.STEPS) - 1:
            self.current_step += 1
            self._render_step()

    def _prev_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self._render_step()

    def _finish(self):
        ui.run_javascript("localStorage.setItem('pybi_onboarded', 'true');")
        self.dialog.close()

    def check_auto_open(self):
        """Auto launch onboarding wizard for first-time users."""
        ui.run_javascript("if (!localStorage.getItem('pybi_onboarded')) { emitEvent('auto_onboard'); }")
        ui.on('auto_onboard', self.open)

    def render_button(self):
        """Render a help/welcome button."""
        btn = ui.button(icon='help_outline', on_click=self.open).props('flat dense round')
        btn.tooltip('Welcome & Onboarding Guide')
        return btn
