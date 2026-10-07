"""CSV data connector using Polars."""

from typing import Any, Optional
import polars as pl

CSV_SEPARATORS = {
    "comma": ",",
    "semicolon": ";",
    "tab": "\t",
    "pipe": "|",
}


def detect_csv_separator(filepath: str, sample_lines: int = 5) -> str:
    """Sniff the most likely delimiter by counting characters in the first rows.

    Args:
        filepath: Path to the CSV file.
        sample_lines: Number of leading rows inspected.

    Returns:
        str: The detected single-character delimiter (defaults to ",").
    """
    candidates = (",", ";", "\t", "|")
    counts = {c: 0 for c in candidates}
    try:
        with open(filepath, "rb") as fh:
            for _ in range(sample_lines):
                line = fh.readline()
                if not line:
                    break
                for cand in candidates:
                    counts[cand] += line.count(cand.encode())
    except OSError:
        return ","
    best, best_count = ",", 0
    for cand, count in counts.items():
        if count > best_count:
            best, best_count = cand, count
    return best


def read_csv(filepath: str, separator: Optional[str] = None, **kwargs: Any) -> pl.DataFrame:
    """Read CSV file into a Polars DataFrame.

    Args:
        filepath: Path to the CSV file.
        separator: One of 'auto', 'comma', 'semicolon', 'tab', 'pipe', or a
            raw single-character delimiter. 'auto' (and None) sniff the file.
        **kwargs: Additional keyword arguments passed to polars.read_csv.

    Returns:
        pl.DataFrame: The loaded DataFrame.
    """
    if separator is None:
        separator = "auto"
    separator = CSV_SEPARATORS.get(separator, separator)
    if separator == "auto":
        separator = detect_csv_separator(filepath)
    kwargs.setdefault("truncate_ragged_lines", True)
    if separator:
        kwargs["separator"] = separator
    return pl.read_csv(filepath, **kwargs)