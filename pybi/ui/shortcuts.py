"""Keyboard shortcuts definitions and tooltips for PyBI."""

SHORTCUTS = {
    'Ctrl+S': 'Save current project / pipeline / layout',
    'Ctrl+Z': 'Undo last action',
    'Ctrl+Y': 'Redo last action',
    'Ctrl+N': 'Create new project',
    'Ctrl+F': 'Focus search bar',
    'F5': 'Execute pipeline / refresh data',
}


def render_shortcuts_help_button():
    """Render a helpful dialog listing available keyboard shortcuts."""
    from nicegui import ui

    with ui.dialog() as dialog, ui.card().classes('w-96 p-4'):
        ui.label('Keyboard Shortcuts').classes('text-lg font-bold mb-3')
        with ui.column().classes('w-full gap-2'):
            for key, desc in SHORTCUTS.items():
                with ui.row().classes('w-full justify-between items-center text-sm'):
                    ui.label(key).classes('font-mono bg-gray-200 dark:bg-gray-700 px-2 py-1 rounded text-xs')
                    ui.label(desc).classes('text-gray-600 dark:text-gray-300')
        ui.button('Close', on_click=dialog.close).props('flat dense').classes('mt-4 align-self-end')

    btn = ui.button(icon='keyboard', on_click=dialog.open).props('flat dense round')
    btn.tooltip('Keyboard Shortcuts')
    return btn
