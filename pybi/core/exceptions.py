"""Custom exception classes for PyBI."""


class PYBIError(Exception):
    """Base exception for PyBI."""



class CompilationError(PYBIError):
    """Raised when the compiler fails to translate a DAG into SQL."""



class FoldingError(CompilationError):
    """Raised when an ETL node cannot be folded into SQL."""



class ValidationError(PYBIError):
    """Raised when a node or pipeline configuration is invalid."""

