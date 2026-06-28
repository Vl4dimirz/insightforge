"""
Insights endpoints — the platform's headline feature.

  • POST /insights/file → upload CSV/Excel → profile → AI analysis.
  • POST /insights/url  → scrape a table from a URL → profile → AI analysis.

Both chain everything built so far: data + scraping + the AI layer.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from app.data import load_dataframe, clean, profile, DataError
from app.scrape import scrape_table, ScrapeError
from app.insights import analyze_profile
from app.ai import AIError

router = APIRouter(prefix="/insights", tags=["Insights"])

MAX_BYTES = 10 * 1024 * 1024


class InsightResult(BaseModel):
    source: str
    rows: int
    columns: int
    insights: str


class UrlInsightRequest(BaseModel):
    url: str
    question: str | None = None


def _insights_from_df(df, source: str, question: str | None) -> InsightResult:
    if df.empty:
        raise HTTPException(status_code=400, detail="No usable rows to analyze.")
    p = profile(df)
    try:
        text = analyze_profile(p, question)
    except AIError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return InsightResult(source=source, rows=p["rows"], columns=p["columns"], insights=text)


@router.post("/file", response_model=InsightResult)
async def insights_file(
    file: UploadFile = File(...),
    question: str | None = Form(None),
) -> InsightResult:
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")
    try:
        df = clean(load_dataframe(file.filename, content))
    except DataError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _insights_from_df(df, file.filename, question)


@router.post("/url", response_model=InsightResult)
def insights_url(req: UrlInsightRequest) -> InsightResult:
    try:
        df = clean(scrape_table(req.url))
    except ScrapeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _insights_from_df(df, f"{req.url} (table)", req.question)
