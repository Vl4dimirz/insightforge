"""
The data layer — load a spreadsheet, clean it, and profile it with pandas.

pandas is the workhorse of Python data work: it loads CSV/Excel into a
"DataFrame" (think a programmable spreadsheet) and lets you analyze it in a
couple of lines. This module is pure data engineering — no AI yet (that's Phase 4).
"""

import io
import math

import pandas as pd


class DataError(ValueError):
    """Raised when a file can't be read as a table."""


def load_dataframe(filename: str, content: bytes) -> pd.DataFrame:
    """Turn raw uploaded bytes into a DataFrame, picking the reader by extension."""
    name = (filename or "").lower()
    try:
        if name.endswith(".csv"):
            return pd.read_csv(io.BytesIO(content))
        if name.endswith((".xlsx", ".xls")):
            return pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise DataError(f"Couldn't read '{filename}': {e}") from e
    raise DataError("Unsupported file type — upload a .csv or .xlsx file.")


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Light, safe cleanup: tidy column names, drop fully-empty rows/columns."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(axis=0, how="all")   # rows where every cell is empty
    df = df.dropna(axis=1, how="all")   # columns where every cell is empty
    return df


def _clean_number(value) -> float | None:
    """Convert a numpy/pandas number to a plain float, turning NaN into None for JSON."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else round(f, 4)


def profile(df: pd.DataFrame) -> dict:
    """Build a structured summary of the table — the heart of Phase 2."""
    rows = int(len(df))
    columns_out = []

    for col in df.columns:
        series = df[col]
        non_null = int(series.notna().sum())
        nulls = int(series.isna().sum())
        col_info = {
            "name": str(col),
            "dtype": str(series.dtype),
            "non_null": non_null,
            "nulls": nulls,
            "null_pct": round((nulls / rows) * 100, 2) if rows else 0.0,
            "unique": int(series.nunique(dropna=True)),
            "sample": [str(v) for v in series.dropna().unique()[:5]],
            "numeric": None,
        }
        # If the column is numeric, add real statistics.
        if pd.api.types.is_numeric_dtype(series):
            col_info["numeric"] = {
                "min": _clean_number(series.min()),
                "max": _clean_number(series.max()),
                "mean": _clean_number(series.mean()),
                "median": _clean_number(series.median()),
                "std": _clean_number(series.std()),
            }
        columns_out.append(col_info)

    return {
        "rows": rows,
        "columns": int(df.shape[1]),
        "duplicate_rows": int(df.duplicated().sum()),
        "column_profiles": columns_out,
    }
