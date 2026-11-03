# 🧠 Semantic Layer, DAX Engine & RLS Specifications

## 1. Semantic Model Structure
The PyBI Semantic Model (`semantic_model.yaml`) defines tables, columns, calculated measures, relationships, and Row-Level Security (RLS) rules.

### YAML Schema Example
```yaml
name: sales_model
tables:
  - name: Sales
    columns:
      - name: SalesID
        data_type: number
        is_key: true
      - name: Amount
        data_type: number
      - name: Date
        data_type: datetime
    measures:
      - name: TotalSales
        expression: "SUM(Sales[Amount])"
        label: "Total Sales"
      - name: SalesYTD
        expression: "TOTALYTD(SUM(Sales[Amount]), Sales[Date])"
        label: "Sales YTD"
relationships:
  - from_table: Sales
    from_column: CustomerID
    to_table: Customer
    to_column: CustomerID
    cardinality: "*:1"
    is_active: true
rls_rules:
  - table_name: Sales
    expression: "Region = '{user.allowed_regions}'"
```

### Model View Editing

The `/model-editor` canvas supports column-level relationship creation and
selection. Relationship properties include endpoint tables and columns,
cardinality, join type, and active state. Changing either endpoint table refreshes
the corresponding column choices. Relationship creation, property changes, and
deletion are persisted immediately; **Gestisci relazioni** provides per-row
property and delete actions.

Removing a table from the semantic model also removes its relationships and RLS
rules, but leaves the project data file intact. `position_x` and `position_y` on
semantic tables are optional canvas metadata used to restore table layout.
Relationship handles resolve either the semantic column `name` or physical
`column_name`; if neither is present, the editor uses a table-edge handle.

---

## 2. DAX-to-SQL Translation Engine (`DaxEngine`)
The canonical `DaxEngine` (`pybi/semantic/dax_translator.py`) uses an extensible decorator-based registry pattern (`@DaxEngine.register`) to translate DAX expressions into DuckDB SQL fragments. The old `pybi.core` DAX modules are compatibility exports; `backend.core.*` import paths have been removed.

### Core Supported DAX Functions
- **DIVIDE(numerator, denominator, [alternate]):** Translates to `COALESCE(num / NULLIF(den, 0), alt)`.
- **IF(condition, true_val, [false_val]):** Translates to `CASE WHEN cond THEN true_val ELSE false_val END`.
- **AVERAGE(column):** Translates to `AVG(column)`.
- **COUNTROWS([table_or_column]):** Translates to `COUNT(column)` or `COUNT(*)`.
- **CALCULATE(expression, [filters...]):** Base expression translation with filter context delegated to query resolver.
- **RELATED(column):** Cross-table column referencing resolved via active relationships.
- **SUMX(table, expression):** Iterative measure aggregation `SUM(expression)`.
- **FILTER(table, condition):** Conditional sub-filtering.
- **TOTALYTD(expression, date_column):** Window-based year-to-date calculation `SUM(expr) OVER (PARTITION BY YEAR(date_col) ORDER BY date_col)`.

---

## 3. Dynamic Row-Level Security (RLS)
The `RLSEngine` (`pybi/semantic/rls.py`) handles claim-based query filters and semantic security roles. Security role schemas are defined in `pybi/semantic/security_models.py`.
