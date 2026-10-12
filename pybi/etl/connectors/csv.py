"""CSV data connector using Polars."""

import os
import re
from typing import Any, Optional
import polars as pl

CSV_SEPARATORS = {
    "comma": ",",
    "semicolon": ";",
    "tab": "\t",
    "pipe": "|",
}

_INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")
_DECIMAL_PATTERN = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
_LENIENT_NUMERIC_PATTERN = re.compile(r"^[+-]?\d[\d.]*(?:,\d+)?$")


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
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV file not found: {filepath}")
    if separator != ",":
        # Non-comma files commonly carry Italian-style decimal separators
        # (e.g. "362,14"). Read everything as string and restore numeric
        # types with ',' handled as the decimal separator.
        kwargs["separator"] = separator
        raw = pl.read_csv(filepath, infer_schema_length=0, **kwargs)
        return _normalize_decimal_commas(raw)
    if separator:
        kwargs["separator"] = separator
    return pl.read_csv(filepath, **kwargs)


def _normalize_decimal_commas(df: pl.DataFrame) -> pl.DataFrame:
    """Restore numeric types, treating ',' as a decimal separator.

    Only columns that look entirely numeric (optionally using ',' for the
    decimal part) are converted; other columns stay strings.
    """
    out = {}
    for name in df.columns:
        raw_vals = df[name].to_list()
        cleaned = [None if v in (None, "") else str(v).strip() for v in raw_vals]
        non_empty = [v for v in cleaned if v is not None]
        if not non_empty:
            out[name] = pl.Series(name, [None] * len(raw_vals), dtype=pl.Float64)
            continue
        if all(_INTEGER_PATTERN.match(v) for v in non_empty):
            out[name] = df[name].cast(pl.Int64)
        elif all(_DECIMAL_PATTERN.match(v) for v in non_empty):
            out[name] = df[name].cast(pl.Float64)
        elif any("," in v for v in non_empty) and all(_LENIENT_NUMERIC_PATTERN.match(v) for v in non_empty):
            normalized = [v.replace(".", "").replace(",", ".") if v else None for v in cleaned]
            out[name] = pl.Series(name, normalized, dtype=pl.Utf8).cast(pl.Float64)
        else:
            out[name] = df[name]
    if not out:
        return df
    return pl.DataFrame(out)