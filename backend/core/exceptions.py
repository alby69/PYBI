"""Compatibility facade for :mod:`pybi.core.exceptions`."""

from backend._compat import alias_module as _alias_module

_alias_module(__name__, "pybi.core.exceptions")
