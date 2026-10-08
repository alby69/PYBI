"""Dashboard exporter for HTML, PNG, PDF and sharing links with Phase 5 Export Engine integration."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from nicegui import ui

from pybi.export_engine.engine import default_export_engine


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


def render_export_dialog(project_id: str, layout: List[Dict[str, Any]], filter_context: Optional[Any] = None):
    """Render Phase 5 export dialog with multi-format, template selection, and background status tracking."""
    with ui.dialog() as dialog, ui.card().classes('w-full max-w-md p-4'):
        ui.label('Publish & Export Engine').classes('text-lg font-bold mb-1')
        ui.label('Export project state with immutable SHA-256 snapshot and template support.').classes('text-xs text-gray-500 mb-3')

        format_select = ui.select(
            options={
                'pdf': 'PDF Document (*.pdf)',
                'html': 'HTML Report (*.html)',
                'md': 'Markdown Knowledge Document (*.md)',
                'csv': 'CSV Data Extract (*.csv)',
            },
            value='pdf',
            label='Export Format'
        ).classes('w-full mb-2')

        template_select = ui.select(
            options={
                'report_dati.html': 'report_dati.html (Dashboard & Metrics)',
                'documento_knowledge.md': 'documento_knowledge.md (Wiki / Knowledge)',
            },
            value='report_dati.html',
            label='Jinja2 Template'
        ).classes('w-full mb-2')

        ai_prompt_input = ui.input(
            label='AI Compilation Prompt (Optional)',
            placeholder='e.g. Include DAX metrics and summarize regional trends...'
        ).classes('w-full mb-3')

        status_container = ui.column().classes('w-full p-2 bg-gray-50 rounded border text-xs text-gray-700 hidden')
        status_label = ui.label('').classes('font-semibold')
        spinner = ui.spinner(size='sm').classes('hidden')

        def trigger_export():
            fmt = format_select.value or 'pdf'
            tpl = template_select.value or ('report_dati.html' if fmt in ['pdf', 'html'] else 'documento_knowledge.md')
            prompt = ai_prompt_input.value

            payload = {
                'title': f'Dashboard Export - {project_id}',
                'widgets': layout,
            }

            status_container.remove_classes('hidden')
            status_label.set_text('Generazione in corso (Submitting job)...')
            spinner.remove_classes('hidden')

            export_id = default_export_engine.submit_export_job(
                project_id=project_id,
                payload=payload,
                filter_context=filter_context,
                export_format=fmt,
                template_id=tpl,
                ai_prompt=prompt,
            )

            ui.timer(0.5, lambda: check_status(export_id), once=False)

        def check_status(export_id: str):
            info = default_export_engine.get_job_status(export_id)
            if not info:
                status_label.set_text('Status: Error finding job')
                spinner.add_classes('hidden')
                return

            st = info.get('status')
            prog = info.get('progress', 0)
            if st == 'completed':
                spinner.add_classes('hidden')
                status_label.set_text(f'Completato! Export ID: {export_id}')
                file_p = info.get('file_path')
                if file_p and Path(file_p).exists():
                    p = Path(file_p)
                    with open(p, 'rb') as f:
                        content_bytes = f.read()
                    ui.download(content_bytes, p.name)
                    ui.notify(f'Export saved and downloaded: {p.name}', type='positive')
            elif st == 'failed':
                spinner.add_classes('hidden')
                err = info.get('error', 'Unknown error')
                status_label.set_text(f'Failed: {err}')
                ui.notify(f'Export failed: {err}', type='negative')
            else:
                status_label.set_text(f'Generazione in corso... ({prog}%)')

        with ui.column().classes('w-full gap-2 mt-2'):
            ui.button('Generate & Download Export', icon='bolt', on_click=trigger_export).props('color=primary w-full')

            with ui.row().classes('w-full gap-2 mt-2'):
                ui.button(
                    'Quick JSON',
                    icon='code',
                    on_click=lambda: ui.download(
                        DashboardExporter.export_to_json(layout).encode('utf-8'),
                        f"dashboard_{project_id}.json"
                    )
                ).props('color=secondary outline dense classes="flex-1"')

                ui.button(
                    'Share Link',
                    icon='share',
                    on_click=lambda: ui.notify(f"Share link: {DashboardExporter.generate_share_link(project_id)}", type='info')
                ).props('color=positive flat dense classes="flex-1"')

        ui.button('Close', on_click=dialog.close).props('flat dense').classes('mt-4 align-self-end')

    btn = ui.button('Export', icon='download', on_click=dialog.open).props('color=info icon=download')
    return btn
