"""Unit tests for DAX expression translator."""

import pytest
from pybi.model.dax_translator import DaxTranslator
from pybi.model.measures import Measure


def test_translate_divide_basic():
    assert DaxTranslator.translate("DIVIDE(SUM('Sales'[Amount]), SUM('Sales'[Units]))") == (
        'COALESCE(SUM("Sales"."Amount") / NULLIF(SUM("Sales"."Units"), 0), 0)'
    )


def test_translate_divide_with_alternate():
    assert DaxTranslator.translate("DIVIDE(SUM('Sales'[Amount]), SUM('Sales'[Units]), -1)") == (
        'COALESCE(SUM("Sales"."Amount") / NULLIF(SUM("Sales"."Units"), 0), -1)'
    )


def test_translate_divide_nested():
    expr = "DIVIDE(SUM(A), SUM(B) + 1)"
    expected = "COALESCE(SUM(A) / NULLIF(SUM(B) + 1, 0), 0)"
    assert DaxTranslator.translate(expr) == expected


def test_translate_divide_nested_functions():
    expr = "DIVIDE(AVERAGE(A), AVERAGE(B))"
    expected = "COALESCE(AVG(A) / NULLIF(AVG(B), 0), 0)"
    assert DaxTranslator.translate(expr) == expected


def test_translate_if():
    assert DaxTranslator.translate("IF(SUM('Sales'[Amount]) > 100, 1, 0)") == (
        'CASE WHEN SUM("Sales"."Amount") > 100 THEN 1 ELSE 0 END'
    )
    assert DaxTranslator.translate("IF(A > B, 'Yes')") == (
        "CASE WHEN A > B THEN 'Yes' ELSE NULL END"
    )


def test_translate_aggregations():
    assert DaxTranslator.translate("SUM('Sales'[Amount])") == 'SUM("Sales"."Amount")'
    assert DaxTranslator.translate("MIN('Sales'[Price])") == 'MIN("Sales"."Price")'
    assert DaxTranslator.translate("MAX('Sales'[Price])") == 'MAX("Sales"."Price")'
    assert DaxTranslator.translate("DISTINCTCOUNT('Customer'[ID])") == 'COUNT(DISTINCT "Customer"."ID")'
    assert DaxTranslator.translate("COUNTA('Customer'[Name])") == 'COUNT("Customer"."Name")'
    assert DaxTranslator.translate("AVERAGE('Sales'[Amount])") == 'AVG("Sales"."Amount")'


def test_translate_iterators():
    assert DaxTranslator.translate("SUMX('Sales', 'Sales'[Price] * 'Sales'[Qty])") == (
        'SUM("Sales"."Price" * "Sales"."Qty")'
    )
    assert DaxTranslator.translate("AVERAGEX('Sales', 'Sales'[Price] * 'Sales'[Qty])") == (
        'AVG("Sales"."Price" * "Sales"."Qty")'
    )


def test_translate_filter_and_table_functions():
    assert DaxTranslator.translate("FILTER('Sales', 'Sales'[Amount] > 100)") == (
        '("Sales"."Amount" > 100)'
    )
    assert DaxTranslator.translate("ALL('Orders'[Status])") == "1=1"
    assert DaxTranslator.translate("REMOVEFILTERS('Orders'[Status])") == "1=1"
    assert DaxTranslator.translate("VALUES('Customer'[Region])") == 'SELECT DISTINCT "Customer"."Region" FROM "Customer"'


def test_translate_switch():
    # Value matching switch
    sw1 = DaxTranslator.translate("SWITCH('Sales'[Status], \"Active\", 1, \"Pending\", 2, 0)")
    assert sw1 == 'CASE WHEN "Sales"."Status" = \'Active\' THEN 1 WHEN "Sales"."Status" = \'Pending\' THEN 2 ELSE 0 END'

    # True condition switch
    sw2 = DaxTranslator.translate("SWITCH(TRUE(), 'Sales'[Amount] > 100, \"High\", 'Sales'[Amount] > 50, \"Medium\", \"Low\")")
    assert sw2 == "CASE WHEN \"Sales\".\"Amount\" > 100 THEN 'High' WHEN \"Sales\".\"Amount\" > 50 THEN 'Medium' ELSE 'Low' END"


def test_translate_logic_and_text():
    assert DaxTranslator.translate("ISBLANK('Sales'[Discount])") == '("Sales"."Discount" IS NULL)'
    assert DaxTranslator.translate("COALESCE('Sales'[Discount], 0)") == 'COALESCE("Sales"."Discount", 0)'
    assert DaxTranslator.translate("CONCATENATE('Customer'[FirstName], 'Customer'[LastName])") == (
        'CONCAT("Customer"."FirstName", "Customer"."LastName")'
    )
    assert DaxTranslator.translate("UPPER('Customer'[City])") == 'UPPER("Customer"."City")'
    assert DaxTranslator.translate("LOWER('Customer'[City])") == 'LOWER("Customer"."City")'
    assert DaxTranslator.translate("ROUND('Sales'[Price], 2)") == 'ROUND("Sales"."Price", 2)'


def test_translate_time_intelligence():
    assert DaxTranslator.translate("TOTALYTD(SUM('Sales'[Amount]), 'Calendar'[Date])") == (
        'SUM("Sales"."Amount") OVER (PARTITION BY YEAR("Calendar"."Date") ORDER BY "Calendar"."Date")'
    )
    assert DaxTranslator.translate("SAMEPERIODLASTYEAR('Calendar'[Date])") == (
        '("Calendar"."Date" - INTERVAL \'1 year\')'
    )
    assert DaxTranslator.translate("DATEADD('Calendar'[Date], -1, 'year')") == (
        '("Calendar"."Date" + INTERVAL -1 year)'
    )


def test_translate_calculate_and_related():
    assert DaxTranslator.translate("CALCULATE(SUM('Sales'[Amount]), 'Region'[Name] = \"West\")") == (
        'SUM("Sales"."Amount")'
    )
    assert DaxTranslator.translate("RELATED('Customer'[Name])") == '"Customer"."Name"'


def test_translate_complex_nested_dax():
    expr = "DIVIDE(SUM('Sales'[Amount]), CALCULATE(COUNTROWS('Orders'), ALL('Orders'[Status])))"
    expected = 'COALESCE(SUM("Sales"."Amount") / NULLIF(COUNT("Orders"), 0), 0)'
    assert DaxTranslator.translate(expr) == expected


def test_identifier_and_operator_cleaning():
    assert DaxTranslator.translate("'Product'[Brand] = \"Proseware\"") == '"Product"."Brand" = \'Proseware\''
    assert DaxTranslator.translate("[Sales Amount] > 100") == '"Sales Amount" > 100'
    assert DaxTranslator.translate("'Customer'[FirstName] & \" \" & 'Customer'[LastName]") == (
        '"Customer"."FirstName" || \' \' || "Customer"."LastName"'
    )


def test_parse_args_quotes_and_commas():
    args = DaxTranslator._parse_args("SUM(sales), 'Category, A', \"Region, B\"")
    assert args == ["SUM(sales)", "'Category, A'", '"Region, B"']


def test_fallback_unrecognized_expression():
    assert DaxTranslator.translate("SUM(amount) + 10") == "SUM(amount) + 10"
    assert DaxTranslator.translate("AVERAGE(amount) - COUNTROWS(table)") == "AVG(amount) - COUNT(table)"


def test_measure_to_sql_fragment_integration():
    m1 = Measure(name="Ratio", table_name="sales", expression="DIVIDE(SUM(amount), SUM(qty))")
    assert m1.to_sql_fragment() == "COALESCE(SUM(amount) / NULLIF(SUM(qty), 0), 0)"

    m2 = Measure(name="AvgAmount", table_name="sales", expression="AVERAGE(amount)")
    assert m2.to_sql_fragment() == "AVG(amount)"


def test_error_handling_invalid_arguments():
    with pytest.raises(ValueError, match="DIVIDE requires at least 2 arguments"):
        DaxTranslator.translate("DIVIDE(SUM(sales))")

    with pytest.raises(ValueError, match="IF requires at least 2 arguments"):
        DaxTranslator.translate("IF(A > B)")

    with pytest.raises(ValueError, match="AVERAGE requires 1 argument"):
        DaxTranslator.translate("AVERAGE()")
