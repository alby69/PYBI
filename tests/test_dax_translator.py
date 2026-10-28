"""Unit tests for DAX expression translator."""

import pytest
from pybi.model.dax_translator import DaxTranslator
from pybi.model.measures import Measure


def test_translate_divide_basic():
    assert DaxTranslator.translate("DIVIDE(SUM(sales), SUM(units))") == (
        "COALESCE(SUM(sales) / NULLIF(SUM(units), 0), 0)"
    )


def test_translate_divide_with_alternate():
    assert DaxTranslator.translate("DIVIDE(SUM(sales), SUM(units), -1)") == (
        "COALESCE(SUM(sales) / NULLIF(SUM(units), 0), -1)"
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
    assert DaxTranslator.translate("IF(SUM(sales) > 100, 1, 0)") == (
        "CASE WHEN SUM(sales) > 100 THEN 1 ELSE 0 END"
    )
    assert DaxTranslator.translate("IF(A > B, 'Yes')") == (
        "CASE WHEN A > B THEN 'Yes' ELSE NULL END"
    )


def test_translate_calculate():
    assert DaxTranslator.translate("CALCULATE(SUM(sales), Region='West')") == "SUM(sales)"


def test_translate_related():
    assert DaxTranslator.translate("RELATED(Customer[Name])") == "Customer[Name]"


def test_translate_average():
    assert DaxTranslator.translate("AVERAGE(amount)") == "AVG(amount)"


def test_translate_countrows():
    assert DaxTranslator.translate("COUNTROWS(Orders)") == "COUNT(Orders)"
    assert DaxTranslator.translate("COUNTROWS()") == "COUNT(*)"


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
