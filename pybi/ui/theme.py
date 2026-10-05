"""Design system tokens and theme manager for PyBI."""

from typing import Dict, Any
from nicegui import ui

# Node color themes by kind
NODE_COLORS: Dict[str, Dict[str, str]] = {
    'DataSource': {'bg': '#e0f2fe', 'border': '#0284c7', 'text': '#0369a1', 'icon': '📄'},
    'Filter': {'bg': '#fef3c7', 'border': '#d97706', 'text': '#b45309', 'icon': '⚡'},
    'Select': {'bg': '#ede9fe', 'border': '#7c3aed', 'text': '#6d28d9', 'icon': '🔍'},
    'GroupBy': {'bg': '#fce7f3', 'border': '#db2777', 'text': '#be185d', 'icon': '📊'},
    'Join': {'bg': '#ffedd5', 'border': '#ea580c', 'text': '#c2410c', 'icon': '🔗'},
    'Output': {'bg': '#dcfce7', 'border': '#16a34a', 'text': '#15803d', 'icon': '💾'},
}

SPACING = {
    'xs': '4px',
    'sm': '8px',
    'md': '16px',
    'lg': '24px',
    'xl': '32px'
}

ELEVATION = {
    'low': '0 1px 2px rgba(0,0,0,0.05)',
    'medium': '0 4px 6px rgba(0,0,0,0.1)',
    'high': '0 10px 15px rgba(0,0,0,0.15)'
}

class ThemeManager:
    """Manages dark/light theme state and styling."""

    def __init__(self, dark_mode: bool = False):
        self.is_dark = dark_mode

    def toggle(self):
        """Toggle dark mode."""
        self.is_dark = not self.is_dark
        self.apply()

    def apply(self):
        """Apply dark mode setting to NiceGUI."""
        dark = ui.dark_mode()
        if self.is_dark:
            dark.enable()
        else:
            dark.disable()

    def render_toggle_button(self):
        """Render a toggle button for theme switching."""
        icon = 'dark_mode' if self.is_dark else 'light_mode'
        btn = ui.button(icon=icon, on_click=self.toggle).props('flat dense round')
        btn.tooltip('Toggle Dark/Light Mode')
        return btn

# Global default theme manager instance
default_theme = ThemeManager()
