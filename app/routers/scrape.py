"""
Scraping endpoints.

  • POST /scrape        → structured summary of any web page.
  • POST /scrape/table  → scrape the first table on a page and run it straight
                          through the Phase 2 analyzer (DataProfile). This is the
                          platform coming together: scrape the web → analyze it.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.scrape import scrape_page, scrape_table, ScrapeError
from app.data import clean, profile
from app.routers.data import DataProfile

router = APIRouter(prefix="/scrape", tags=["Scrape"])


class ScrapeRequest(BaseModel):
    url: str = Field(..., description="A full URL, e.g. https://example.com")


class ScrapeResult(BaseModel):
    url: str
    title: str
    description: str
    headings: list[str]
    links_count: int
    images_count: int
    tables_count: int
    text_chars: int
    text_preview: str


@router.post("", response_model=ScrapeResult)
def scrape(req: ScrapeRequest) -> ScrapeResult:
    try:
        return ScrapeResult(**scrape_page(req.url))
    except ScrapeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/table", response_model=DataProfile)
def scrape_and_analyze(req: ScrapeRequest) -> DataProfile:
    try:
        df = clean(scrape_table(req.url))
    except ScrapeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if df.empty:
        raise HTTPException(status_code=400, detail="The scraped table had no usable rows.")
    return DataProfile(filename=f"{req.url} (table)", **profile(df))
