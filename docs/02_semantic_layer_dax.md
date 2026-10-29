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

---

## 2. DAX-to-SQL Translation Engine (`DaxEngine`)
The `DaxEngine` (`backend/core/dax_engine/translator.py`) uses an extensible decorator-based registry pattern (`@DaxEngine.register`) to translate DAX expressions into valid DuckDB SQL fragments.

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
The `RLSEngine` (`backend/core/rls_engine.py`) dynamically sanitizes and injects `WHERE` clauses into query execution based on authenticated JWT user claims (`AuthUser`).
