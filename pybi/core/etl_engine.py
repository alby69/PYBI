"""Re-export ETLEngine for pybi.core.etl_engine import compatibility."""

from pybi.etl.duckdb_engine import ETLEngine

__all__ = ["ETLEngine"]
