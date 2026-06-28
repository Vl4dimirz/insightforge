"""
InsightForge API — application entry point.

Run it locally with:
    uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/docs for interactive, auto-generated API docs.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app import automation
from app.routers import ai, data, scrape, insights, report, automation as automation_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the background scheduler when the API boots, stop it on shutdown.
    automation.start_scheduler()
    yield
    automation.stop_scheduler()


app = FastAPI(
    title=f"{settings.app_name} API",
    description="An AI-powered data & automation platform: AI text, data analysis, web scraping, AI insights, reports, automation.",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow a browser frontend (e.g. a Next.js dashboard) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your real domain before production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai.router)
app.include_router(data.router)
app.include_router(scrape.router)
app.include_router(insights.router)
app.include_router(report.router)
app.include_router(automation_router.router)


@app.get("/health", tags=["System"])
def health() -> dict:
    """Cheap liveness check — handy for uptime monitors and deploys."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "ai_configured": bool(settings.gemini_api_key),
    }
