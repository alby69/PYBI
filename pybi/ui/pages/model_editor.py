"""Semantic Model Editor page implementation for visual Power BI-style Model View & Relationship Editor."""

import os
from typing import Dict, Any, List, Optional
from nicegui import ui

from pybi.semantic.schema import (
    SemanticModel as CoreSemanticModel,
    SemanticTable,
    SemanticColumn,
    SemanticMeasure,
    SemanticRelationship,
    RLSRule,
    Cardinality,
    JoinType,
    autodetect_relationships,
)
from pybi.semantic.relationships import autodetect_model_relationships
from pybi.semantic.model_sync import (
    get_semantic_model_path,
    load_project_semantic_model as _core_load_project_semantic_model,
    save_project_semantic_model,
    sync_etl_outputs_into_model,
)
from pybi.core.storage import default_storage
from pybi.ui.components.project_manager import ProjectManager
from pybi.ui.components.navbar import render_navbar
from pybi.ui.shortcuts import render_shortcuts_help_button
from pybi.ui.theme import default_theme
from pybi.ui.components.model_flow_editor import ModelFlowEditor


def load_project_semantic_model(project_id: str) -> CoreSemanticModel:
    """Load a project model, seeding example tables only before its first save."""
    model = _core_load_project_semantic_model(project_id)
    if not model.tables and not os.path.exists(get_semantic_model_path(project_id)):
        t1 = SemanticTable(
            name='sales',
            source_table='sales_data',
            columns=[
                SemanticColumn(name='sale_id', column_name='sale_id', data_type='integer', is_key=True),
                SemanticColumn(name='store_id', column_name='store_id', data_type='integer', is_key=False),
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
        r1 = SemanticRelationship(
            from_table='sales',
            from_column='store_id',
            to_table='stores',
            to_column='store_id',
            cardinality=Cardinality.MANY_TO_ONE,
            join_type=JoinType.LEFT,
            is_active=True,
        )
        model.tables.extend([t1, t2])
        model.relationships.append(r1)
        sync_etl_outputs_into_model(project_id, model)
    return model


def _resolve_relationship_handle(table: SemanticTable, column_name: str, fallback_handle: str) -> str:
    for column in table.columns:
        if column_name in (column.name, column.column_name):
            return column.name
    return fallback_handle


def _relationship_handle_id(table: SemanticTable, column_name: str, fallback_handle: str, direction: str) -> str:
    handle = _resolve_relationship_handle(table, column_name, fallback_handle)
    return handle if handle == fallback_handle else f'{direction}:{handle}'


def _relationship_column_from_handle(handle_id: Optional[str], direction: str) -> Optional[str]:
    prefix = f'{direction}:'
    if not handle_id or not handle_id.startswith(prefix):
        return None
    return handle_id[len(prefix):]


def create_model_editor_page():
    """Render the Semantic Model View & Visual Relationship Builder page (Power BI style)."""
    render_navbar(active='/model-editor')

    # Big banner header, aligned with the Data (ETL) / Power Query Editor page header.
    with ui.row().classes('w-full items-end justify-between q-mt-sm'):
        with ui.column().classes('gap-0'):
            ui.label('Model View - Visual Table & Relationship Editor').classes('text-2xl font-bold text-slate-900')
            ui.label('Power BI-style visual data modeling: field-level drag-and-drop relationships, reactive properties panel, autodetect & RLS management.').classes('text-sm text-slate-600')
        with ui.row().classes('items-center gap-2'):
            render_shortcuts_help_button()
            default_theme.render_toggle_button()

    current_model: CoreSemanticModel = CoreSemanticModel(name='default_model')
    selected_rel_index: Optional[int] = None
    selected_table_name: Optional[str] = None

    def load_model_for_project():
        nonlocal current_model, selected_rel_index, selected_table_name
        pid = project_manager.project_id
        current_model = load_project_semantic_model(pid)
        selected_rel_index = None
        selected_table_name = None
        refresh_model_ui()
        status_label.set_text(f'State: Model loaded for "{pid}"')

    def handle_project_switch(pid, action):
        load_model_for_project()

    with ui.row().classes('w-full items-center gap-4 q-mb-sm'):
        project_manager = ProjectManager(value='default', on_switch=handle_project_switch)
        ui.space()
        status_label = ui.label('State: Ready').classes('text-xs font-semibold text-blue-700 bg-blue-50 px-2.5 py-1 rounded border border-blue-200')

    with ui.row().classes('w-full gap-2 items-center q-mb-md bg-slate-100 p-2 rounded-lg border border-slate-200'):
        ui.button('Save Model (YAML)', on_click=lambda: save_model()).props('color=positive icon=save dense')
        ui.button('Generate from Schema', on_click=lambda: auto_generate_schema()).props('color=secondary icon=auto_awesome dense')
        ui.button('Aggiungi tabella', on_click=lambda: open_add_table_dialog()).props('color=secondary icon=table_view dense')
        ui.button('Gestisci tabelle', on_click=lambda: open_manage_tables_dialog()).props('color=secondary icon=dataset dense')
        ui.button('Nuova relazione', on_click=lambda: open_add_relationship_dialog()).props('color=primary icon=add_link dense')
        ui.button('Gestisci relazioni', on_click=lambda: open_manage_relationships_dialog()).props('color=primary icon=settings_ethernet dense')
        ui.button('Adatta alla finestra', on_click=lambda: flow_editor.fit_view()).props('color=dark icon=zoom_out_map dense')
        ui.button('Add Measure', on_click=lambda: open_add_measure_dialog()).props('color=info icon=functions dense')
        ui.button('Add RLS Rule', on_click=lambda: open_add_rls_dialog()).props('color=warning icon=security dense')

    # Main Split View: Canvas on Left, Reactive Panel on Right
    with ui.row().classes('w-full gap-4 items-stretch q-mb-md').style('min-height: 600px; display: flex; flex-wrap: nowrap;'):
        with ui.column().classes('flex-1 min-w-0 border rounded-lg bg-white p-2 shadow-sm').style('min-height: 600px; height: 620px;'):
            flow_editor = ModelFlowEditor(nodes=[], edges=[]).classes('w-full h-full')

        with ui.card().classes('w-80 shrink-0 shadow-md border border-slate-300 p-4 bg-white rounded-lg flex flex-col gap-3 overflow-y-auto').style('min-height: 600px; height: 620px;'):
            properties_title = ui.label('Proprietà').classes('font-bold text-base text-slate-800 border-b pb-2 w-full')
            empty_properties = ui.label('Seleziona una tabella o una relazione nel canvas per visualizzarne le proprietà.').classes(
                'text-sm text-slate-500 leading-relaxed'
            )

            relationship_properties = ui.column().classes('w-full gap-3')
            with relationship_properties:
                prop_from_tbl = ui.select([], label='Tabella di Origine (From Table)').classes('w-full')
                prop_from_col = ui.select([], label='Campo di Origine (From Column)').classes('w-full')

                prop_to_tbl = ui.select([], label='Tabella di Destinazione (To Table)').classes('w-full')
                prop_to_col = ui.select([], label='Campo di Destinazione (To Column)').classes('w-full')

                prop_cardinality = ui.select(['1:1', '1:*', '*:1', '*:*'], label='Cardinalità', value='*:1').classes('w-full')
                prop_join_type = ui.select(['LEFT', 'INNER', 'RIGHT', 'FULL'], label='Tipo di Join', value='LEFT').classes('w-full')

                with ui.row().classes('w-full items-center justify-between pt-1'):
                    ui.label('Stato Attivo (Active)').classes('text-xs font-semibold text-slate-700')
                    prop_is_active = ui.switch(value=True).props('dense color=primary')

                with ui.row().classes('w-full gap-2 mt-auto pt-3 border-t'):
                    ui.button('Elimina Relazione', on_click=lambda: delete_selected_relationship()).props('color=negative icon=delete flat dense').classes('w-full')

            table_properties = ui.column().classes('w-full gap-3')
            with table_properties:
                selected_table_label = ui.label('').classes('text-sm font-semibold text-slate-800 break-all')
                ui.label('La rimozione elimina la tabella dal modello e rimuove le relazioni e le regole RLS collegate. Il file sorgente non viene cancellato.').classes('text-xs text-slate-500')
                ui.button('Rimuovi tabella dal modello', on_click=lambda: delete_selected_table()).props('color=negative icon=delete dense').classes('w-full')
            table_properties.set_visibility(False)
            relationship_properties.set_visibility(False)

    # Accordion Sections for Measures, RLS Rules, and YAML Preview
    with ui.expansion('📐 Calculated Measures & Row-Level Security (RLS)', icon='security').classes('w-full q-mb-md bg-white border rounded-lg'):
        rel_container = ui.row().classes('w-full p-4 gap-4 items-start')

    yaml_preview_container = ui.expansion('📄 View/Edit YAML Specification', icon='code').classes('w-full q-mb-md bg-white border rounded-lg')

    def persist_model_state(message: str):
        pid = project_manager.project_id
        filepath = save_project_semantic_model(pid, current_model)
        status_label.set_text(message)
        return filepath

    def save_model():
        pid = project_manager.project_id
        filepath = persist_model_state(f'State: Saved model for "{pid}"')
        ui.notify(f'Semantic model saved to {os.path.basename(filepath)}', type='positive')
        refresh_model_ui()

    def auto_generate_schema():
        pid = project_manager.project_id
        files = default_storage.list_project_files(pid)
        data_dir = default_storage.get_project_data_dir(pid)
        existing_tables = {table.name: table for table in current_model.tables}

        tables = []
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in ['.csv', '.parquet', '.sqlite', '.db']:
                continue
            tbl_name = os.path.splitext(f)[0]
            full_p = os.path.join(data_dir, f)

            cols = []
            measures = []

            try:
                if ext == '.csv':
                    import polars as pl
                    from pybi.etl.connectors import read_csv
                    df = read_csv(full_p, n_rows=100)
                    for col_name, dtype in df.schema.items():
                        col_type = str(dtype).lower()
                        if 'int' in col_type or 'float' in col_type or 'decimal' in col_type or 'double' in col_type:
                            data_type = 'number'
                        elif 'bool' in col_type:
                            data_type = 'boolean'
                        elif 'date' in col_type or 'time' in col_type:
                            data_type = 'datetime'
                        else:
                            data_type = 'string'

                        is_key = col_name.lower().endswith('id') or col_name.lower() == 'id'
                        cols.append(SemanticColumn(name=col_name, column_name=col_name, data_type=data_type, is_key=is_key))

                        # Create default measure for numeric columns
                        if data_type == 'number' and not is_key:
                            measures.append(SemanticMeasure(name=f'sum_{col_name}', expression=f'SUM({col_name})', agg_func='SUM', label=f'Sum of {col_name}'))

                elif ext == '.parquet':
                    import polars as pl
                    schema = pl.scan_parquet(full_p).collect_schema()
                    for col_name, dtype in schema.items():
                        col_type = str(dtype).lower()
                        if 'int' in col_type or 'float' in col_type or 'decimal' in col_type or 'double' in col_type:
                            data_type = 'number'
                        elif 'bool' in col_type:
                            data_type = 'boolean'
                        elif 'date' in col_type or 'time' in col_type:
                            data_type = 'datetime'
                        else:
                            data_type = 'string'

                        is_key = col_name.lower().endswith('id') or col_name.lower() == 'id'
                        cols.append(SemanticColumn(name=col_name, column_name=col_name, data_type=data_type, is_key=is_key))
            except Exception as err:
                print(f"Error inspecting {f}: {err}")

            if not cols:
                cols = [
                    SemanticColumn(name=f'{tbl_name}_id', column_name=f'{tbl_name}_id', data_type='number', is_key=True),
                    SemanticColumn(name='name', column_name='name', data_type='string'),
                    SemanticColumn(name='value', column_name='value', data_type='number')
                ]

            existing = existing_tables.get(tbl_name)
            if existing:
                existing_columns = {
                    column.name: column for column in existing.columns
                }
                cols = [
                    existing_columns[column.name].model_copy(update={
                        'column_name': column.column_name,
                        'data_type': column.data_type,
                    }) if column.name in existing_columns else column
                    for column in cols
                ]
                existing_measure_names = {measure.name for measure in existing.measures}
                measures = [
                    *existing.measures,
                    *(measure for measure in measures if measure.name not in existing_measure_names),
                ]
            tables.append(SemanticTable(
                name=tbl_name,
                source_table=tbl_name,
                position_x=existing.position_x if existing else None,
                position_y=existing.position_y if existing else None,
                width=existing.width if existing else None,
                height=existing.height if existing else None,
                columns=cols,
                measures=measures,
            ))

        if not tables:
            # Fallback default tables if no files exist
            t1 = SemanticTable(
                name='sales',
                source_table='sales_data',
                columns=[
                    SemanticColumn(name='sale_id', column_name='sale_id', data_type='number', is_key=True),
                    SemanticColumn(name='store_id', column_name='store_id', data_type='number', is_key=False),
                    SemanticColumn(name='region', column_name='region', data_type='string'),
                    SemanticColumn(name='amount', column_name='amount', data_type='number'),
                    SemanticColumn(name='cost', column_name='cost', data_type='number'),
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
                    SemanticColumn(name='store_id', column_name='store_id', data_type='number', is_key=True),
                    SemanticColumn(name='store_name', column_name='store_name', data_type='string'),
                    SemanticColumn(name='country', column_name='country', data_type='string'),
                ]
            )
            tables = [t1, t2]
            for table in tables:
                existing = existing_tables.get(table.name)
                if existing:
                    old_columns = {column.name: column for column in existing.columns}
                    table.columns = [
                        old_columns[column.name].model_copy(update={
                            'column_name': column.column_name,
                            'data_type': column.data_type,
                        }) if column.name in old_columns else column
                        for column in table.columns
                    ]
                    table.position_x = existing.position_x
                    table.position_y = existing.position_y
                    table.width = existing.width
                    table.height = existing.height
                    table.measures = existing.measures

        current_model.tables = tables
        # Include ETL query outputs (e.g. "tab_dati") alongside raw data files.
        sync_etl_outputs_into_model(pid, current_model)
        table_names = {table.name for table in current_model.tables}
        table_columns = {
            table.name: {column.name for column in table.columns}
            for table in current_model.tables
        }
        current_model.relationships = [
            relationship for relationship in current_model.relationships
            if relationship.from_table in table_names
            and relationship.to_table in table_names
            and relationship.from_column in table_columns[relationship.from_table]
            and relationship.to_column in table_columns[relationship.to_table]
        ]
        current_model.rls_rules = [rule for rule in current_model.rls_rules if rule.target_table in table_names]
        if current_model.default_table not in table_names:
            current_model.default_table = current_model.tables[0].name if current_model.tables else None
        # Autodetect relationships between newly generated tables
        new_rels = autodetect_relationships(current_model.tables, current_model.relationships)
        if new_rels:
            current_model.relationships.extend(new_rels)

        ui.notify('Schema generated automatically from real data files!', type='positive')
        save_model()

    def update_columns_for_table(table_name: str, dropdown_target: ui.select):
        tbl = current_model.get_table(table_name)
        cols = [column.name for column in tbl.columns] if tbl else []
        current_value = dropdown_target.value
        selected_value = current_value if current_value in cols else (cols[0] if cols else None)
        dropdown_target.set_options(cols, value=selected_value)

    def on_from_table_change(e):
        update_columns_for_table(e.value, prop_from_col)
        update_selected_relationship_from_ui(from_table=e.value, from_column=prop_from_col.value)

    def on_to_table_change(e):
        update_columns_for_table(e.value, prop_to_col)
        update_selected_relationship_from_ui(to_table=e.value, to_column=prop_to_col.value)

    prop_from_tbl.on_value_change(on_from_table_change)
    prop_to_tbl.on_value_change(on_to_table_change)
    prop_from_col.on_value_change(lambda e: update_selected_relationship_from_ui(from_column=e.value))
    prop_to_col.on_value_change(lambda e: update_selected_relationship_from_ui(to_column=e.value))
    prop_cardinality.on_value_change(lambda e: update_selected_relationship_from_ui(cardinality=e.value))
    prop_join_type.on_value_change(lambda e: update_selected_relationship_from_ui(join_type=e.value))
    prop_is_active.on_value_change(lambda e: update_selected_relationship_from_ui(is_active=e.value))

    def populate_properties_panel(rel_idx: Optional[int]):
        nonlocal selected_rel_index, selected_table_name
        if rel_idx is None or not 0 <= rel_idx < len(current_model.relationships):
            selected_rel_index = None
            selected_table_name = None
            properties_title.set_text('Proprietà')
            relationship_properties.set_visibility(False)
            table_properties.set_visibility(False)
            empty_properties.set_visibility(True)
            return

        selected_rel_index = rel_idx
        selected_table_name = None
        properties_title.set_text('Proprietà Relazione')
        empty_properties.set_visibility(False)
        relationship_properties.set_visibility(True)
        table_properties.set_visibility(False)
        tables = [t.name for t in current_model.tables]
        prop_from_tbl.set_options(tables)
        prop_to_tbl.set_options(tables)

        r = current_model.relationships[rel_idx]
        prop_from_tbl.value = r.from_table
        update_columns_for_table(r.from_table, prop_from_col)
        prop_from_col.value = r.from_column

        prop_to_tbl.value = r.to_table
        update_columns_for_table(r.to_table, prop_to_col)
        prop_to_col.value = r.to_column

        card = r.cardinality.value if isinstance(r.cardinality, Cardinality) else str(r.cardinality)
        jtype = r.join_type.value if isinstance(r.join_type, JoinType) else str(r.join_type)
        prop_cardinality.value = card
        prop_join_type.value = jtype
        prop_is_active.value = getattr(r, 'is_active', True)

    def update_selected_relationship_from_ui(
        from_table=None,
        from_column=None,
        to_table=None,
        to_column=None,
        cardinality=None,
        join_type=None,
        is_active=None,
    ):
        if selected_rel_index is None or selected_rel_index < 0 or selected_rel_index >= len(current_model.relationships):
            return
        r = current_model.relationships[selected_rel_index]
        updated_from_table = from_table if from_table is not None else r.from_table
        updated_from_column = from_column if from_column is not None else r.from_column
        updated_to_table = to_table if to_table is not None else r.to_table
        updated_to_column = to_column if to_column is not None else r.to_column
        if any(
            idx != selected_rel_index and (
                (rel.from_table, rel.from_column, rel.to_table, rel.to_column)
                == (updated_from_table, updated_from_column, updated_to_table, updated_to_column)
                or (rel.from_table, rel.from_column, rel.to_table, rel.to_column)
                == (updated_to_table, updated_to_column, updated_from_table, updated_from_column)
            )
            for idx, rel in enumerate(current_model.relationships)
        ):
            ui.notify('Questa relazione esiste già nel modello.', type='warning')
            populate_properties_panel(selected_rel_index)
            return
        r.from_table = updated_from_table
        r.from_column = updated_from_column
        r.to_table = updated_to_table
        r.to_column = updated_to_column
        if cardinality is not None:
            r.cardinality = cardinality
        if join_type is not None:
            r.join_type = join_type
        if is_active is not None:
            r.is_active = is_active

        # Update edges visual style
        refresh_canvas_edges()
        persist_model_state('State: Relationship updated')

    def delete_selected_relationship():
        if selected_rel_index is not None:
            delete_relationship_at(selected_rel_index)

    def delete_relationship_at(rel_idx: int):
        nonlocal selected_rel_index
        if rel_idx < 0 or rel_idx >= len(current_model.relationships):
            return False
        relationship = current_model.relationships.pop(rel_idx)
        selected_rel_index = None
        refresh_canvas_edges()
        persist_model_state('State: Relationship deleted')
        refresh_model_ui()
        ui.notify(
            f'Relazione {relationship.from_table}.{relationship.from_column} → '
            f'{relationship.to_table}.{relationship.to_column} eliminata',
            type='positive',
        )
        return True

    def handle_node_click(e):
        nonlocal selected_rel_index, selected_table_name
        node = e.args.get('node', {})
        node_data = node.get('data') or {}
        selected_table_name = node.get('id') or node_data.get('name')
        if not selected_table_name:
            return
        selected_rel_index = None
        table = current_model.get_table(selected_table_name)
        if table:
            properties_title.set_text('⚙️ Proprietà Tabella')
            selected_table_label.set_text(f'{table.name} · sorgente: {table.source_table}')
            empty_properties.set_visibility(False)
            relationship_properties.set_visibility(False)
            table_properties.set_visibility(True)

    def handle_pane_click(_e):
        populate_properties_panel(None)

    def open_add_table_dialog():
        project_id = project_manager.project_id
        data_dir = default_storage.get_project_data_dir(project_id)
        available_files = [
            filename for filename in default_storage.list_project_files(project_id)
            if os.path.splitext(filename)[1].lower() in {'.csv', '.parquet'}
            and os.path.splitext(filename)[0] not in {table.name for table in current_model.tables}
        ]
        if not available_files:
            ui.notify('Nessuna nuova sorgente CSV o Parquet disponibile. Carica prima un file in Data (ETL).', type='info')
            return

        dialog = ui.dialog()
        with dialog, ui.card().classes('w-[min(90vw,480px)] p-5 gap-3'):
            ui.label('Aggiungi tabella al modello').classes('text-lg font-bold text-slate-800')
            ui.label('Seleziona una sorgente dati già caricata nel progetto.').classes('text-sm text-slate-500')
            source_file = ui.select(
                available_files,
                label='File sorgente',
                value=available_files[0],
                with_input=True,
            ).classes('w-full')

            def add_table():
                filename = source_file.value
                if filename not in available_files:
                    ui.notify('Seleziona un file sorgente valido.', type='warning')
                    return
                table_name = os.path.splitext(filename)[0]
                full_path = os.path.join(data_dir, filename)
                try:
                    import polars as pl

                    if filename.lower().endswith('.csv'):
                        from pybi.etl.connectors import read_csv
                        schema = read_csv(full_path, n_rows=100).schema
                    else:
                        schema = pl.scan_parquet(full_path).collect_schema()
                except Exception as err:
                    ui.notify(f'Impossibile leggere lo schema di "{filename}": {err}', type='negative')
                    return

                columns = []
                for column_name, dtype in schema.items():
                    type_name = str(dtype).lower()
                    if any(token in type_name for token in ('int', 'float', 'decimal', 'double')):
                        data_type = 'number'
                    elif 'bool' in type_name:
                        data_type = 'boolean'
                    elif 'date' in type_name or 'time' in type_name:
                        data_type = 'datetime'
                    else:
                        data_type = 'string'
                    columns.append(SemanticColumn(
                        name=column_name,
                        column_name=column_name,
                        data_type=data_type,
                        is_key=column_name.lower() == 'id' or column_name.lower().endswith('_id'),
                    ))

                if not columns:
                    ui.notify(f'Il file "{filename}" non contiene colonne leggibili.', type='warning')
                    return
                current_model.tables.append(SemanticTable(
                    name=table_name,
                    source_table=table_name,
                    columns=columns,
                ))
                if current_model.default_table is None:
                    current_model.default_table = table_name
                dialog.close()
                save_model()
                ui.notify(f'Tabella "{table_name}" aggiunta al modello.', type='positive')

            with ui.row().classes('w-full justify-end gap-2 pt-2'):
                ui.button('Annulla', on_click=dialog.close).props('flat')
                ui.button('Aggiungi tabella', on_click=add_table).props('color=primary icon=add')
        dialog.open()

    def open_add_relationship_dialog():
        tables = [table.name for table in current_model.tables]
        if len(tables) < 2:
            ui.notify('Servono almeno due tabelle nel modello per creare una relazione.', type='warning')
            return

        dialog = ui.dialog()
        with dialog, ui.card().classes('w-[min(90vw,560px)] p-5 gap-3'):
            ui.label('Crea relazione').classes('text-lg font-bold text-slate-800')
            ui.label('Scegli le due tabelle e le colonne che contengono la chiave corrispondente.').classes(
                'text-sm text-slate-500'
            )
            from_table = ui.select(tables, label='Tabella di origine', value=tables[0]).classes('w-full')
            from_column = ui.select([], label='Colonna di origine').classes('w-full')
            to_table = ui.select(tables, label='Tabella di destinazione', value=tables[1]).classes('w-full')
            to_column = ui.select([], label='Colonna di destinazione').classes('w-full')
            cardinality = ui.select(
                ['1:1', '1:*', '*:1', '*:*'],
                label='Cardinalità',
                value='*:1',
            ).classes('w-full')
            join_type = ui.select(
                ['LEFT', 'INNER', 'RIGHT', 'FULL'],
                label='Tipo di join',
                value='LEFT',
            ).classes('w-full')
            is_active = ui.switch('Relazione attiva', value=True)

            def update_dialog_columns(table_select, column_select):
                table = current_model.get_table(table_select.value)
                columns = [column.name for column in table.columns] if table else []
                column_select.set_options(columns, value=columns[0] if columns else None)

            update_dialog_columns(from_table, from_column)
            update_dialog_columns(to_table, to_column)
            from_table.on_value_change(lambda _e: update_dialog_columns(from_table, from_column))
            to_table.on_value_change(lambda _e: update_dialog_columns(to_table, to_column))

            def add_relationship_from_dialog():
                if from_table.value == to_table.value:
                    ui.notify('Scegli due tabelle diverse.', type='warning')
                    return
                rel_index = create_relationship(
                    from_table.value,
                    from_column.value,
                    to_table.value,
                    to_column.value,
                    cardinality.value,
                    join_type.value,
                    is_active.value,
                )
                if rel_index is not None:
                    dialog.close()

            with ui.row().classes('w-full justify-end gap-2 pt-2'):
                ui.button('Annulla', on_click=dialog.close).props('flat')
                ui.button('Crea relazione', on_click=add_relationship_from_dialog).props('color=primary icon=add_link')
        dialog.open()

    def remove_table_from_model(table_name: str):
        nonlocal selected_rel_index, selected_table_name
        if not table_name or not current_model.get_table(table_name):
            return False
        current_model.tables = [table for table in current_model.tables if table.name != table_name]
        current_model.relationships = [
            relationship for relationship in current_model.relationships
            if relationship.from_table != table_name and relationship.to_table != table_name
        ]
        current_model.rls_rules = [rule for rule in current_model.rls_rules if rule.target_table != table_name]
        if current_model.default_table == table_name:
            current_model.default_table = current_model.tables[0].name if current_model.tables else None
        selected_rel_index = None
        selected_table_name = None
        save_model()
        ui.notify(f'Tabella "{table_name}" rimossa dal modello', type='positive')
        return True

    def delete_selected_table():
        if selected_table_name:
            remove_table_from_model(selected_table_name)

    def open_manage_tables_dialog():
        dialog = ui.dialog()
        with dialog, ui.card().classes('w-[min(90vw,720px)] max-h-[85vh] p-4 gap-3'):
            with ui.row().classes('w-full items-center justify-between border-b border-slate-200 pb-2'):
                with ui.column().classes('gap-0'):
                    ui.label('Gestisci tabelle').classes('text-lg font-bold text-slate-800')
                    ui.label(f'{len(current_model.tables)} tabelle nel modello').classes('text-xs text-slate-500')
                ui.button(icon='close', on_click=dialog.close).props('flat round dense aria-label="Chiudi gestione tabelle"')

            if not current_model.tables:
                ui.label('Il modello non contiene tabelle. Aggiungine una da una sorgente CSV/Parquet o genera lo schema.').classes(
                    'w-full rounded border border-dashed border-slate-300 bg-slate-50 p-5 text-center text-sm text-slate-500'
                )
            else:
                with ui.column().classes('w-full gap-2 overflow-y-auto'):
                    for table in current_model.tables:
                        with ui.row().classes('table-management-entry w-full items-center gap-3 rounded border border-slate-200 bg-white px-3 py-2'):
                            with ui.column().classes('min-w-0 flex-grow gap-0'):
                                ui.label(table.name).classes('truncate text-sm font-semibold text-slate-800')
                                ui.label(
                                    f'Sorgente: {table.source_table} · {len(table.columns)} colonne · '
                                    f'{sum(1 for rel in current_model.relationships if rel.from_table == table.name or rel.to_table == table.name)} relazioni'
                                ).classes('truncate text-xs text-slate-500')
                            ui.button(
                                'Proprietà',
                                icon='tune',
                                on_click=lambda name=table.name: select_table_from_manager(name, dialog),
                            ).props('flat dense color=primary')
                            ui.button(
                                'Rimuovi',
                                icon='delete',
                                on_click=lambda name=table.name: remove_table_from_manager(name, dialog),
                            ).props('flat dense color=negative')

            with ui.row().classes('w-full justify-between items-center mt-2 pt-2 border-t'):
                ui.button('Aggiungi tabella', icon='add', on_click=lambda: open_add_table_from_manager(dialog)).props(
                    'color=primary dense'
                )
                ui.button('Chiudi', on_click=dialog.close).props('flat dense')
        dialog.open()

    def select_table_from_manager(table_name: str, dialog):
        nonlocal selected_rel_index, selected_table_name
        selected_table_name = table_name
        selected_rel_index = None
        table = current_model.get_table(table_name)
        if table:
            properties_title.set_text('Proprietà Tabella')
            selected_table_label.set_text(f'{table.name} · sorgente: {table.source_table}')
            empty_properties.set_visibility(False)
            relationship_properties.set_visibility(False)
            table_properties.set_visibility(True)
        dialog.close()

    def remove_table_from_manager(table_name: str, dialog):
        dialog.close()
        remove_table_from_model(table_name)

    def open_add_table_from_manager(dialog):
        dialog.close()
        open_add_table_dialog()

    def handle_node_drag_stop(e):
        node = e.args.get('node', {})
        position = node.get('position') or {}
        table = current_model.get_table(node.get('id'))
        if not table or 'x' not in position or 'y' not in position:
            return
        table.position_x = float(position['x'])
        table.position_y = float(position['y'])
        save_project_semantic_model(project_manager.project_id, current_model)
        status_label.set_text(f'State: Position saved for "{table.name}"')

    def handle_node_resize_stop(e):
        node = e.args.get('node', {})
        table = current_model.get_table(node.get('id'))
        width = node.get('width')
        height = node.get('height')
        if not table or not isinstance(width, (int, float)) or not isinstance(height, (int, float)):
            return
        table.width = float(width)
        table.height = float(height)
        save_project_semantic_model(project_manager.project_id, current_model)
        status_label.set_text(f'State: Dimensions saved for "{table.name}"')

    def refresh_canvas_edges():
        edges = []
        for idx, r in enumerate(current_model.relationships):
            from_table = current_model.get_table(r.from_table)
            to_table = current_model.get_table(r.to_table)
            if not from_table or not to_table:
                continue
            card = r.cardinality.value if isinstance(r.cardinality, Cardinality) else str(r.cardinality)
            jtype = r.join_type.value if isinstance(r.join_type, JoinType) else str(r.join_type)
            is_act = getattr(r, 'is_active', True)
            edge_color = '#0f766e' if is_act else '#94a3b8'

            edges.append({
                'id': f'rel_{r.from_table}_{r.from_column}_{r.to_table}_{r.to_column}_{idx}',
                'source': r.from_table,
                'sourceHandle': _relationship_handle_id(from_table, r.from_column, '__table_source__', 'source'),
                'sourcePosition': 'right',
                'target': r.to_table,
                'targetHandle': _relationship_handle_id(to_table, r.to_column, '__table_target__', 'target'),
                'targetPosition': 'left',
                'label': card,
                'labelStyle': {'fill': '#0f172a', 'fontWeight': 700, 'fontSize': '11px'},
                'labelBgStyle': {'fill': '#ffffff', 'fillOpacity': 0.95},
                'markerEnd': {'type': 'arrowclosed', 'color': edge_color},
                'data': {
                    'rel_index': idx,
                    'from_table': r.from_table,
                    'from_column': r.from_column,
                    'to_table': r.to_table,
                    'to_column': r.to_column,
                    'cardinality': card,
                    'join_type': jtype,
                    'is_active': is_act,
                },
                'style': {
                    'stroke': edge_color,
                    'strokeWidth': 2.5,
                    'strokeDasharray': 'none' if is_act else '5,5',
                }
            })
        flow_editor.edges = edges

    def refresh_model_ui():
        # Build Vue Flow Nodes from tables
        nodes = []
        x_offset = 50
        y_offset = 50

        for idx, tbl in enumerate(current_model.tables):
            nodes.append({
                'id': tbl.name,
                'type': 'table_card',
                'style': {
                    'width': f'{tbl.width or 280}px',
                    **({'height': f'{tbl.height}px'} if tbl.height is not None else {}),
                },
                'position': {
                    'x': tbl.position_x if tbl.position_x is not None else x_offset + (idx % 3) * 320,
                    'y': tbl.position_y if tbl.position_y is not None else y_offset + (idx // 3) * 350,
                },
                'data': {
                    'label': tbl.name,
                    'source_table': tbl.source_table,
                    'is_fact': any(token in tbl.name.lower() for token in ('fact', 'sales', 'orders', 'transactions')),
                    'columns': [c.model_dump(mode='json') for c in tbl.columns],
                    'measures': [m.model_dump(mode='json') for m in tbl.measures],
                }
            })
        flow_editor.nodes = nodes
        refresh_canvas_edges()
        populate_properties_panel(selected_rel_index)

        # Render Measures & RLS section
        rel_container.clear()
        with rel_container:
            # Measures table
            with ui.column().classes('flex-1'):
                ui.label('Calculated Measures:').classes('font-semibold text-sm text-slate-700 mb-1')
                meas_rows = []
                for tbl in current_model.tables:
                    for m in tbl.measures:
                        meas_rows.append({
                            'table': tbl.name,
                            'name': m.name,
                            'expression': m.expression or m.agg_func,
                            'label': m.label or ''
                        })
                if not meas_rows:
                    ui.label('No measures defined.').classes('text-xs text-slate-500 italic')
                else:
                    cols = [
                        {'name': 'table', 'label': 'Table', 'field': 'table', 'align': 'left'},
                        {'name': 'name', 'label': 'Measure Name', 'field': 'name', 'align': 'left'},
                        {'name': 'expression', 'label': 'Expression', 'field': 'expression', 'align': 'left'},
                        {'name': 'label', 'label': 'Label', 'field': 'label', 'align': 'left'},
                    ]
                    ui.table(columns=cols, rows=meas_rows, row_key='name').classes('w-full')

            # RLS Rules table
            with ui.column().classes('flex-1'):
                ui.label('Row-Level Security (RLS) Rules:').classes('font-semibold text-sm text-slate-700 mb-1')
                if not current_model.rls_rules:
                    ui.label('No RLS rules defined.').classes('text-xs text-slate-500 italic')
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

        # Code editor preview
        yaml_preview_container.clear()
        with yaml_preview_container:
            yaml_str = current_model.to_yaml()
            ui.code(yaml_str, language='yaml').classes('w-full text-xs font-mono bg-slate-900 text-green-300 p-3 rounded')

    # Event handlers for Vue Flow canvas
    def create_relationship(from_table, from_column, to_table, to_column, cardinality, join_type, is_active=True):
        source = current_model.get_table(from_table)
        target = current_model.get_table(to_table)
        if not source or not target or from_table == to_table:
            ui.notify('Scegli due tabelle diverse presenti nel modello.', type='warning')
            return None
        if from_column not in {column.name for column in source.columns} or to_column not in {
            column.name for column in target.columns
        }:
            ui.notify('Scegli una colonna valida per ciascuna tabella.', type='warning')
            return None
        if any(
            (rel.from_table, rel.from_column, rel.to_table, rel.to_column)
            in {
                (from_table, from_column, to_table, to_column),
                (to_table, to_column, from_table, from_column),
            }
            for rel in current_model.relationships
        ):
            ui.notify('Questa relazione esiste già nel modello.', type='warning')
            return None

        current_model.relationships.append(SemanticRelationship(
            from_table=from_table,
            from_column=from_column,
            to_table=to_table,
            to_column=to_column,
            cardinality=cardinality,
            join_type=join_type,
            is_active=is_active,
        ))
        rel_index = len(current_model.relationships) - 1
        populate_properties_panel(rel_index)
        persist_model_state('State: Relationship created')
        refresh_model_ui()
        ui.notify(f'Relazione creata: {from_table}.{from_column} → {to_table}.{to_column}', type='positive')
        return rel_index

    def handle_on_connect(e):
        conn = e.args.get('connection', {})
        source_tbl = conn.get('source')
        source_col = _relationship_column_from_handle(conn.get('sourceHandle'), 'source')
        target_tbl = conn.get('target')
        target_col = _relationship_column_from_handle(conn.get('targetHandle'), 'target')
        if source_tbl and source_col and target_tbl and target_col:
            create_relationship(
                source_tbl, source_col, target_tbl, target_col,
                Cardinality.MANY_TO_ONE, JoinType.LEFT,
            )

    def handle_edge_click(e):
        edge = e.args.get('edge', {})
        data = edge.get('data', {})
        idx = data.get('rel_index')
        if idx is not None:
            populate_properties_panel(idx)
        else:
            # Match edge parameters
            src_tbl = edge.get('source')
            src_col = _relationship_column_from_handle(edge.get('sourceHandle'), 'source')
            tgt_tbl = edge.get('target')
            tgt_col = _relationship_column_from_handle(edge.get('targetHandle'), 'target')
            for i, r in enumerate(current_model.relationships):
                if r.from_table == src_tbl and r.from_column == src_col and r.to_table == tgt_tbl and r.to_column == tgt_col:
                    populate_properties_panel(i)
                    break

    flow_editor.on_connect(handle_on_connect)
    flow_editor.on_node_click(handle_node_click)
    flow_editor.on_pane_click(handle_pane_click)
    flow_editor.on_node_drag_stop(handle_node_drag_stop)
    flow_editor.on_node_resize_stop(handle_node_resize_stop)
    flow_editor.on_edge_click(handle_edge_click)

    # Dialogs
    def open_manage_relationships_dialog():
        dialog = ui.dialog()
        with dialog, ui.card().classes('w-[min(90vw,850px)] max-h-[85vh] p-4 gap-3'):
            with ui.row().classes('w-full items-center justify-between border-b border-slate-200 pb-2'):
                with ui.column().classes('gap-0'):
                    ui.label('Gestisci relazioni').classes('text-lg font-bold text-slate-800')
                    ui.label(f'{len(current_model.relationships)} relazioni nel modello').classes('text-xs text-slate-500')
                with ui.row().classes('items-center gap-1'):
                    ui.button('Nuova relazione', icon='add_link', on_click=lambda: open_add_relationship_from_manager(dialog)).props(
                        'color=primary dense'
                    )
                    ui.button(icon='close', on_click=dialog.close).props('flat round dense aria-label="Chiudi"')

            if not current_model.relationships:
                ui.label('Nessuna relazione definita. Collega due colonne nel canvas o usa il rilevamento automatico.').classes(
                    'w-full rounded border border-dashed border-slate-300 bg-slate-50 p-5 text-center text-sm text-slate-500'
                )
            else:
                with ui.column().classes('w-full gap-2 overflow-y-auto'):
                    for idx, relationship in enumerate(current_model.relationships):
                        cardinality = relationship.cardinality.value if isinstance(relationship.cardinality, Cardinality) else str(relationship.cardinality)
                        join_type = relationship.join_type.value if isinstance(relationship.join_type, JoinType) else str(relationship.join_type)
                        active = getattr(relationship, 'is_active', True)
                        with ui.row().classes('relationship-entry w-full items-center gap-3 rounded border border-slate-200 bg-white px-3 py-2'):
                            with ui.column().classes('min-w-0 flex-grow gap-0'):
                                ui.label(f'{relationship.from_table}.{relationship.from_column}  →  {relationship.to_table}.{relationship.to_column}').classes(
                                    'truncate font-mono text-xs font-semibold text-slate-800'
                                )
                                ui.label(f'{cardinality} · {join_type} · {"Attiva" if active else "Inattiva"}').classes(
                                    'text-[11px] text-slate-500'
                                )
                            ui.button(
                                'Proprietà',
                                icon='tune',
                                on_click=lambda index=idx: select_relationship_from_manager(index, dialog),
                            ).props('flat dense color=primary')
                            ui.button(
                                'Elimina',
                                icon='delete',
                                on_click=lambda index=idx: delete_relationship_from_manager(index, dialog),
                            ).props('flat dense color=negative')

            def run_autodetect():
                new_rels = autodetect_relationships(current_model.tables, current_model.relationships)
                if not new_rels:
                    ui.notify('Nessuna nuova relazione rilevata automaticamente.', type='info')
                else:
                    current_model.relationships.extend(new_rels)
                    ui.notify(f'Rilevate {len(new_rels)} nuove relazioni automaticamente!', type='positive')
                    save_model()
                    dialog.close()

            with ui.row().classes('w-full justify-between items-center mt-3 pt-2 border-t'):
                ui.button('Rileva automaticamente', on_click=run_autodetect).props('color=secondary icon=auto_awesome dense')
                with ui.row().classes('gap-2'):
                    ui.button('Chiudi', on_click=dialog.close).props('flat dense')
        dialog.open()

    def select_relationship_from_manager(rel_idx: int, dialog):
        populate_properties_panel(rel_idx)
        dialog.close()

    def open_add_relationship_from_manager(dialog):
        dialog.close()
        open_add_relationship_dialog()

    def delete_relationship_from_manager(rel_idx: int, dialog):
        if delete_relationship_at(rel_idx):
            dialog.close()

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
            m_expr = ui.input('Expression / Formula', value='SUM(amount) - SUM(cost)').classes('w-full')
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
