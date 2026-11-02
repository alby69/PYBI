"""Helpers for preserving historical backend imports."""

from importlib import import_module
import sys
from types import ModuleType


def alias_module(module_name: str, target_name: str) -> ModuleType:
    """Resolve a historical backend module to its canonical pybi module."""
    module = import_module(target_name)
    sys.modules[module_name] = module
    return module
