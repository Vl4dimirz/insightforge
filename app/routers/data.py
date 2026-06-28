"""
Data endpoints.

POST /data/analyze — upload a CSV/Excel file and get back a structured profile:
row/column counts, per-column types, missing values, uniqueness, sample values,
and real statistics for numeric columns. This is the foundation the AI insights
layer (Phase 4) will later explain in plain language.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.data import load_dataframe, clean, profile, DataError

router = APIRouter(prefix="/data", tags=["Data"])


class NumericStats(BaseModel):
    min: float | None
    max: float | None
    mean: float | None
    median: float | None
    std: float | None


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    non_null: int
    nulls: int
    null_pct: float
    unique: int
    sample: list[str]
    numeric: NumericStats | None


class DataProfile(BaseModel):
    filename: str
    rows: int
    columns: int
    duplicate_rows: int
    column_profiles: list[ColumnProfile]


# 10 MB cap — refuse anything larger before we read it into memory.
MAX_BYTES = 10 * 1024 * 1024


@router.post("/analyze", response_model=DataProfile)
async def analyze(file: UploadFile = File(...)) -> DataProfile:
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")
    try:
        df = clean(load_dataframe(file.filename, content))
    except DataError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if df.empty:
        raise HTTPException(status_code=400, detail="The file has no usable rows.")

    return DataProfile(filename=file.filename, **profile(df))
