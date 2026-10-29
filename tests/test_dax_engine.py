"""Unit tests for backend.core.dax_engine.DaxEngine."""

import pytest
from backend.core.dax_engine import DaxEngine


def test_dax_engine_divide():
    assert DaxEngine.translate("DIVIDE(SUM(sales), SUM(units))") == (
        "COALESCE(SUM(sales) / NULLIF(SUM(units), 0), 0)"
    )
    assert DaxEngine.translate("DIVIDE(SUM(sales), SUM(units), 99)") == (
        "COALESCE(SUM(sales) / NULLIF(SUM(units), 0), 99)"
    )


def test_dax_engine_sumx():
    assert DaxEngine.translate("SUMX(Sales, Sales[Price] * Sales[Qty])") == (
        "SUM(Sales[Price] * Sales[Qty])"
    )


def test_dax_engine_filter():
    assert DaxEngine.translate("FILTER(Sales, Sales[Amount] > 100)") == (
        "(Sales[Amount] > 100)"
    )


def test_dax_engine_totalytd():
    assert DaxEngine.translate("TOTALYTD(SUM(Sales[Amount]), Calendar[Date])") == (
        "SUM(Sales[Amount]) OVER (PARTITION BY YEAR(Calendar[Date]) ORDER BY Calendar[Date])"
    )


def test_dax_engine_custom_registration():
    @DaxEngine.register("CUSTOMFUNC")
    def _translate_custom(args, model=None):
        return f"CUSTOM_SQL({args[0]})"

    assert DaxEngine.translate("CUSTOMFUNC(col_a)") == "CUSTOM_SQL(col_a)"


def test_dax_engine_arg_parsing_complex():
    args = DaxEngine._parse_args("SUM(sales, 'sub, val'), FILTER(t, col = \"a, b\"), 100")
    assert len(args) == 3
    assert args[0] == "SUM(sales, 'sub, val')"
    assert args[1] == 'FILTER(t, col = "a, b")'
    assert args[2] == "100"
