"""PyBI Semantic Data Model domain module."""

import warnings

from pybi.semantic.dax_translator import DaxEngine, DaxTranslator
from pybi.semantic.measures import Measure, MeasureEvaluator
from pybi.semantic.model_engine import ModelEngine
from pybi.semantic.runtime_schema import Column, DataType, Relationship, SemanticModel, Table

warnings.warn(
    "The 'pybi.model' package is deprecated; import semantic types from 'pybi.semantic'.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "Column",
    "DataType",
    "DaxTranslator",
    "DaxEngine",
    "Measure",
    "MeasureEvaluator",
    "ModelEngine",
    "Relationship",
    "SemanticModel",
    "Table",
]
