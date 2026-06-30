"""
Autonomous research agent endpoint.

  • POST /agent/research → give it a goal and a few URLs; it plans, scrapes each
    page, and writes one grounded comparative report — running the whole loop
    itself. This is scrape + AI + analysis composed into a single agent.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent import run_agent, MAX_URLS
from app.ai import AIError
from app.scrape import ScrapeError

router = APIRouter(prefix="/agent", tags=["Agent"])


class ResearchRequest(BaseModel):
    goal: str = Field(..., description="What the agent should find out, in plain English.",
                      examples=["Compare these competitors and summarize each one's strengths and weaknesses."])
    urls: list[str] = Field(..., description=f"1 to {MAX_URLS} full URLs to investigate.",
                            examples=[["https://example.com", "https://example.org"]])


class AgentStep(BaseModel):
    phase: str
    summary: str
    detail: str = ""


class AgentResult(BaseModel):
    goal: str
    focus: list[str]
    steps: list[AgentStep]
    sources: list[dict]
    report: str


@router.post("/research", response_model=AgentResult)
def research(req: ResearchRequest) -> AgentResult:
    try:
        return AgentResult(**run_agent(req.goal, req.urls))
    except ValueError as e:
        # bad input (no goal / no usable URLs) or all-URLs-failed
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ScrapeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except AIError as e:
        # most often Gemini's free-tier quota — tell the caller plainly
        raise HTTPException(
            status_code=503,
            detail=f"The AI step is unavailable right now (often the free-tier quota). Try again shortly. ({e})",
        ) from e
