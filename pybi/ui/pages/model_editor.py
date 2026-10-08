"""Semantic Model Editor page implementation for visual model builder and YAML management."""

import os
from typing import Dict, Any, List, Optional
import yaml
from nicegui import ui

from pybi.core.semantic_model import (
    SemanticModel as CoreSemanticModel,
    SemanticTable,
    SemanticColumn,
    SemanticMeasure,
    SemanticRelationship,
    RLSRule,
    Cardinality,
    JoinType,
)
from pybi.core.storage import default_storage
from pybi.ui.components.project_manager import ProjectManager
from pybi.ui.components.navbar import render_navbar
from pybi.ui.shortcuts import render_shortcuts_help_button
from pybi.ui.theme import default_theme


def get_semantic_model_path(project_id: str) -> str:
    """Get path to semantic_model.yaml for a given project."""
    data_dir = default_storage.get_project_data_dir(project_id)
    return os.path.join(data_dir, "semantic_model.yaml")


def load_project_semantic_model(project_id: str) -> CoreSemanticModel:
    """Load semantic model for project, or create a default model if not existing."""
    filepath = get_semantic_model_path(project_id)
    if os.path.exists(filepath):
        try:
            return CoreSemanticModel.load_yaml_file(filepath)
        except Exception:
            pass
    return CoreSemanticModel(name=f"{project_id}_semantic_model", tables=[], relationships=[], rls_rules=[])


def save_project_semantic_model(project_id: str, model: CoreSemanticModel) -> str:
    """Save semantic model to project storage directory."""
    filepath = get_semantic_model_path(project_id)
    model.save_yaml_file(filepath)
    return filepath


def create_model_editor_page():
    """Render the Semantic Model View & Visual Relationship Builder page."""
    render_navbar(active='/model-editor')
    ui.label('Model View - Semantic Layer & Relationship Builder').classes('text-2xl font-bold q-mb-sm')
    ui.label('Define semantic tables, visual relationships, calculated measures, and Row-Level Security (RLS) rules.').classes('text-gray-600 q-mb-md')

    current_model: CoreSemanticModel = CoreSemanticModel(name='default_model')

    def load_model_for_project():
        nonlocal current_model
        pid = project_manager.project_id
        current_model = load_project_semantic_model(pid)
        refresh_model_ui()
        status_label.set_text(f'State: Model loaded for "{pid}"')

    def handle_project_switch(pid, action):
        load_model_for_project()

    with ui.row().classes('w-full items-center gap-4 q-mb-md'):
        project_manager = ProjectManager(value='default', on_switch=handle_project_switch)
        ui.space()
        status_label = ui.label('State: Ready').classes('text-sm font-semibold text-blue-700')

    with ui.row().classes('w-full gap-2 items-center q-mb-md'):
        ui.button('Save Model (YAML)', on_click=lambda: save_model()).props('color=positive icon=save')
        ui.button('Generate from Schema', on_click=lambda: auto_generate_schema()).props('color=secondary icon=auto_awesome')
        ui.button('Add Relationship', on_click=lambda: open_add_relationship_dialog()).props('color=primary icon=add')
        ui.button('Add Measure', on_click=lambda: open_add_measure_dialog()).props('color=info icon=functions')
        ui.button('Add RLS Rule', on_click=lambda: open_add_rls_dialog()).props('color=warning icon=security')
        ui.separator().props('vertical')
        render_shortcuts_help_button()
        default_theme.render_toggle_button()

    # Cards layout container
    tables_container = ui.row().classes('w-full gap-4 q-mb-md items-start')
    rel_container = ui.card().classes('w-full q-mb-md p-4')
    yaml_preview_container = ui.expansion('📄 View/Edit YAML Specification', icon='code').classes('w-full q-mb-md')

    def save_model():
        pid = project_manager.project_id
        filepath = save_project_semantic_model(pid, current_model)
        ui.notify(f'Semantic model saved to {os.path.basename(filepath)}', type='positive')
        status_label.set_text(f'State: Saved model for "{pid}"')
        refresh_model_ui()

    def auto_generate_schema():
        pid = project_manager.project_id
        files = default_storage.list_project_files(pid)
        if not files:
            # Fallback sample tables
            t1 = SemanticTable(
                name='sales',
                source_table='sales_data',
                columns=[
                    SemanticColumn(name='sale_id', column_name='sale_id', data_type='integer', is_key=True),
                    SemanticColumn(name='store_id', column_name='store_id', data_type='integer', is_key=True),
                    SemanticColumn(name='region', column_name='region', data_type='string'),
                    SemanticColumn(name='amount', column_name='amount', data_type='float'),
                    SemanticColumn(name='cost', column_name='cost', data_type='float'),
                ],
                measures=[
                    SemanticMeasure(name='Total_Sales', expression='SUM(amount)', agg_func='SUM', label='Total Sales'),
                    SemanticMeasure(name='Margine_Lordo', expression='SUM(amount) - SUM(cost)', agg_func='CUSTOM', label='Margine Lordo')
                ]
            )
            t2 = SemanticTable(
                name='stores',
                source_table='store_dim',
                columns=[
                    SemanticColumn(name='store_id', column_name='store_id', data_type='integer', is_key=True),
                    SemanticColumn(name='store_name', column_name='store_name', data_type='string'),
                    SemanticColumn(name='country', column_name='country', data_type='string'),
                ]
            )
            current_model.tables = [t1, t2]
            current_model.relationships = [
                SemanticRelationship(
                    from_table='sales',
                    from_column='store_id',
                    to_table='stores',
                    to_column='store_id',
                    cardinality=Cardinality.MANY_TO_ONE,
                    join_type=JoinType.LEFT
                )
            ]
        else:
            tables = []
            for f in files:
                tbl_name = os.path.splitext(f)[0]
                cols = [
                    SemanticColumn(name=f'{tbl_name}_id', column_name=f'{tbl_name}_id', data_type='integer', is_key=True),
                    SemanticColumn(name='name', column_name='name', data_type='string'),
                    SemanticColumn(name='value', column_name='value', data_type='float')
                ]
                meas = [
                    SemanticMeasure(name=f'total_{tbl_name}', expression='SUM(value)', agg_func='SUM')
                ]
                tables.append(SemanticTable(name=tbl_name, source_table=tbl_name, columns=cols, measures=meas))
            current_model.tables = tables

        ui.notify('Schema generated automatically!', type='positive')
        save_model()

    def refresh_model_ui():
        # 1. Render Tables as visual Cards
        tables_container.clear()
        with tables_container:
            if not current_model.tables:
                ui.label('No tables in semantic model. Click "Generate from Schema" or load project data files.').classes('text-gray-500 italic p-4')
            else:
                for tbl in current_model.tables:
                    with ui.card().classes('w-72 shadow-md border border-blue-200 p-3 bg-white'):
                        with ui.row().classes('w-full items-center justify-between border-b pb-2 mb-2'):
                            ui.label(f'📊 {tbl.name}').classes('font-bold text-base text-blue-800')
                            ui.label(f'[{tbl.source_table}]').classes('text-xs text-gray-500')

                        ui.label('Columns / Dimensions:').classes('text-xs font-semibold text-gray-600 mt-1')
                        with ui.column().classes('w-full gap-1 pl-2 mb-2'):
                            for col in tbl.columns:
                                key_badge = '🔑 ' if col.is_key else '  '
                                ui.label(f'{key_badge}{col.name} ({col.data_type})').classes('text-xs font-mono text-gray-700')

                        if tbl.measures:
                            ui.label('Calculated Measures:').classes('text-xs font-semibold text-gray-600 mt-1')
                            with ui.column().classes('w-full gap-1 pl-2'):
                                for m in tbl.measures:
                                    ui.label(f'📐 {m.name}: {m.expression or m.agg_func}').classes('text-xs font-mono text-blue-600')

        # 2. Render Relationships & RLS Rules
        rel_container.clear()
        with rel_container:
            ui.label('Visual Table Relationships & RLS Rules').classes('font-bold text-lg q-mb-xs text-gray-800')

            with ui.row().classes('w-full gap-4 items-start'):
                # Relationships table
                with ui.column().classes('flex-1'):
                    ui.label('Relationships:').classes('font-semibold text-sm text-gray-700 mb-1')
                    if not current_model.relationships:
                        ui.label('No relationships defined.').classes('text-xs text-gray-500 italic')
                    else:
                        rel_rows = []
                        for idx, r in enumerate(current_model.relationships):
                            card = r.cardinality.value if isinstance(r.cardinality, Cardinality) else str(r.cardinality)
                            jtype = r.join_type.value if isinstance(r.join_type, JoinType) else str(r.join_type)
                            rel_rows.append({
                                'id': idx,
                                'from': f'{r.from_table}.{r.from_column}',
                                'cardinality': card,
                                'to': f'{r.to_table}.{r.to_column}',
                                'join_type': jtype
                            })
                        cols = [
                            {'name': 'from', 'label': 'From Key', 'field': 'from', 'align': 'left'},
                            {'name': 'cardinality', 'label': 'Cardinality', 'field': 'cardinality', 'align': 'center'},
                            {'name': 'to', 'label': 'To Key', 'field': 'to', 'align': 'left'},
                            {'name': 'join_type', 'label': 'Join Type', 'field': 'join_type', 'align': 'center'}
                        ]
                        ui.table(columns=cols, rows=rel_rows, row_key='id').classes('w-full')

                # RLS Rules table
                with ui.column().classes('flex-1'):
                    ui.label('Row-Level Security (RLS) Rules:').classes('font-semibold text-sm text-gray-700 mb-1')
                    if not current_model.rls_rules:
                        ui.label('No RLS rules defined.').classes('text-xs text-gray-500 italic')
                    else:
                        rls_rows = [
                            {'name': r.name, 'target_table': r.target_table, 'filter': r.filter_expression}
                            for r in current_model.rls_rules
                        ]
                        cols = [
                            {'name': 'name', 'label': 'Rule Name', 'field': 'name', 'align': 'left'},
                            {'name': 'target_table', 'label': 'Target Table', 'field': 'target_table', 'align': 'left'},
                            {'name': 'filter', 'label': 'Filter Expression', 'field': 'filter', 'align': 'left'}
                        ]
                        ui.table(columns=cols, rows=rls_rows, row_key='name').classes('w-full')

        # 3. YAML Code Editor/Preview
        yaml_preview_container.clear()
        with yaml_preview_container:
            yaml_str = current_model.to_yaml()
            ui.code(yaml_str, language='yaml').classes('w-full text-xs font-mono bg-gray-900 text-green-300 p-3 rounded')

    # Dialogs
    def open_add_relationship_dialog():
        tables = [t.name for t in current_model.tables]
        if len(tables) < 2:
            ui.notify('Need at least 2 tables to define a relationship. Run "Generate from Schema" first.', type='warning')
            return

        dialog = ui.dialog()
        with dialog, ui.card().classes('w-96 p-4 gap-3'):
            ui.label('Add Relationship').classes('text-lg font-bold')
            from_tbl = ui.select(tables, label='From Table', value=tables[0]).classes('w-full')
            from_col = ui.input('From Column', value='store_id').classes('w-full')
            to_tbl = ui.select(tables, label='To Table', value=tables[1] if len(tables) > 1 else tables[0]).classes('w-full')
            to_col = ui.input('To Column', value='store_id').classes('w-full')
            cardinality = ui.select(['1:1', '1:*', '*:1', '*:*'], label='Cardinality', value='*:1').classes('w-full')
            join_type = ui.select(['LEFT', 'INNER', 'RIGHT', 'FULL'], label='Join Type', value='LEFT').classes('w-full')

            def save_rel():
                rel = SemanticRelationship(
                    from_table=from_tbl.value,
                    from_column=from_col.value,
                    to_table=to_tbl.value,
                    to_column=to_col.value,
                    cardinality=cardinality.value,
                    join_type=join_type.value
                )
                current_model.relationships.append(rel)
                dialog.close()
                save_model()

            with ui.row().classes('w-full justify-end gap-2 mt-2'):
                ui.button('Cancel', on_click=dialog.close).props('flat dense')
                ui.button('Add', on_click=save_rel).props('color=primary dense')
        dialog.open()

    def open_add_measure_dialog():
        tables = [t.name for t in current_model.tables]
        if not tables:
            ui.notify('Create a table first.', type='warning')
            return

        dialog = ui.dialog()
        with dialog, ui.card().classes('w-96 p-4 gap-3'):
            ui.label('Add Calculated Measure').classes('text-lg font-bold')
            target_tbl = ui.select(tables, label='Target Table', value=tables[0]).classes('w-full')
            m_name = ui.input('Measure Name', value='Margine_Lordo').classes('w-full')
            m_expr = ui.input('Expression / DAX SQL Formula', value='SUM(amount) - SUM(cost)').classes('w-full')
            m_agg = ui.select(['SUM', 'AVG', 'COUNT', 'MIN', 'MAX', 'CUSTOM'], label='Aggregation Func', value='CUSTOM').classes('w-full')
            m_label = ui.input('Display Label', value='Margine Lordo').classes('w-full')

            def save_m():
                tbl = current_model.get_table(target_tbl.value)
                if tbl:
                    meas = SemanticMeasure(
                        name=m_name.value,
                        expression=m_expr.value,
                        agg_func=m_agg.value,
                        label=m_label.value
                    )
                    tbl.measures.append(meas)
                    dialog.close()
                    save_model()

            with ui.row().classes('w-full justify-end gap-2 mt-2'):
                ui.button('Cancel', on_click=dialog.close).props('flat dense')
                ui.button('Add Measure', on_click=save_m).props('color=primary dense')
        dialog.open()

    def open_add_rls_dialog():
        tables = [t.name for t in current_model.tables]
        if not tables:
            ui.notify('Create a table first.', type='warning')
            return

        dialog = ui.dialog()
        with dialog, ui.card().classes('w-96 p-4 gap-3'):
            ui.label('Add RLS Rule').classes('text-lg font-bold')
            rule_name = ui.input('Rule Name', value='restrict_user_region').classes('w-full')
            target_tbl = ui.select(tables, label='Target Table', value=tables[0]).classes('w-full')
            filter_expr = ui.input('Filter Expression', value="region = '{user_allowed_region}'").classes('w-full')

            def save_rls():
                rule = RLSRule(
                    name=rule_name.value,
                    target_table=target_tbl.value,
                    filter_expression=filter_expr.value
                )
                current_model.rls_rules.append(rule)
                dialog.close()
                save_model()

            with ui.row().classes('w-full justify-end gap-2 mt-2'):
                ui.button('Cancel', on_click=dialog.close).props('flat dense')
                ui.button('Add RLS Rule', on_click=save_rls).props('color=warning dense')
        dialog.open()

    # Initial load
    load_model_for_project()
