"""Compatibility facade for :mod:`pybi.etl.connectors.sqlite`."""

from backend._compat import alias_module as _alias_module

_alias_module(__name__, "pybi.etl.connectors.sqlite")
