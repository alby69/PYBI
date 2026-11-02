"""Deprecated compatibility entry point for the canonical :mod:`pybi` package."""

import warnings

from pybi import __version__

warnings.warn(
    "The 'backend' package is deprecated; import from 'pybi' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["__version__"]
