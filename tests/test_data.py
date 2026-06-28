"""Unit tests for the data layer — offline, no AI or network needed."""

import pandas as pd

from app.data import clean, profile


def test_profile_counts_and_stats():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "y"]})
    p = profile(df)

    assert p["rows"] == 3
    assert p["columns"] == 2
    assert p["duplicate_rows"] == 0

    cols = {c["name"]: c for c in p["column_profiles"]}
    assert cols["a"]["numeric"]["mean"] == 2.0   # (1+2+3)/3
    assert cols["a"]["numeric"]["max"] == 3.0
    assert cols["b"]["unique"] == 2              # x, y
    assert cols["b"]["numeric"] is None


def test_profile_flags_missing_values():
    df = pd.DataFrame({"q": [1.0, None, 3.0]})
    col = profile(df)["column_profiles"][0]
    assert col["nulls"] == 1
    assert col["null_pct"] == round((1 / 3) * 100, 2)


def test_clean_drops_all_empty_columns():
    df = pd.DataFrame({"a": [1, 2], "empty": [None, None]})
    out = clean(df)
    assert "empty" not in out.columns
    assert "a" in out.columns
