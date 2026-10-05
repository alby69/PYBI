"""Dashboard exporter for HTML, PNG, PDF and sharing links."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from nicegui import ui


class DashboardExporter:
    """Exporter utility for generating standalone HTML or export configurations."""

    @staticmethod
    def export_to_json(layout: List[Dict[str, Any]], indent: int = 2) -> str:
        """Export dashboard layout to formatted JSON string."""
        return json.dumps(layout, indent=indent)

    @staticmethod
    def export_to_html(title: str, layout: List[Dict[str, Any]]) -> str:
        """Generate standalone HTML document representing the dashboard layout."""
        widgets_html = []
        for w in layout:
            w_title = w.get('title', 'Widget')
            w_type = w.get('type', 'kpi')
            w_val = w.get('value', '')
            w_sub = w.get('subtitle', '')
            widgets_html.append(f"""
            <div class="widget">
                <h3>{w_title} ({w_type.upper()})</h3>
                <p><strong>Value:</strong> {w_val}</p>
                <p><em>{w_sub}</em></p>
            </div>
            """)

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <title>{title}</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; padding: 24px; background: #f9fafb; color: #111827; }}
        h1 {{ font-size: 24px; margin-bottom: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }}
        .widget {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="grid">
        {"".join(widgets_html)}
    </div>
</body>
</html>
"""
        return html_content

    @staticmethod
    def generate_share_link(project_id: str) -> str:
        """Generate share link URL for public viewer."""
        return f"/viewer?project={project_id}"


def render_export_dialog(project_id: str, layout: List[Dict[str, Any]]):
    """Render export dialog with options for HTML, JSON, and Share link."""
    with ui.dialog() as dialog, ui.card().classes('w-96 p-4'):
        ui.label('Export Dashboard').classes('text-lg font-bold mb-3')

        with ui.column().classes('w-full gap-2'):
            ui.button(
                'Download HTML',
                icon='code',
                on_click=lambda: ui.download(
                    DashboardExporter.export_to_html(f"Dashboard - {project_id}", layout).encode('utf-8'),
                    f"dashboard_{project_id}.html"
                )
            ).props('color=primary outline w-full')

            ui.button(
                'Download JSON',
                icon='description',
                on_click=lambda: ui.download(
                    DashboardExporter.export_to_json(layout).encode('utf-8'),
                    f"dashboard_{project_id}.json"
                )
            ).props('color=secondary outline w-full')

            ui.button(
                'Copy Share Link',
                icon='share',
                on_click=lambda: ui.notify(f"Share link: {DashboardExporter.generate_share_link(project_id)}", type='info')
            ).props('color=positive flat w-full')

        ui.button('Close', on_click=dialog.close).props('flat dense').classes('mt-4 align-self-end')

    btn = ui.button('Export', icon='download', on_click=dialog.open).props('color=info icon=download')
    return btn
