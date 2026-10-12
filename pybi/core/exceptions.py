"""Custom exception classes for PyBI."""


class PYBIError(Exception):
    """Base exception for PyBI."""

    pass


class CompilationError(PYBIError):
    """Raised when the compiler fails to translate a DAG into SQL."""

    pass


class FoldingError(CompilationError):
    """Raised when an ETL node cannot be folded into SQL."""

    pass


class ValidationError(PYBIError):
    """Raised when a node or pipeline configuration is invalid."""

    pass
