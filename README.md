# InsightForge

An AI-powered **data & automation platform**, built in Python.

> Repo: https://github.com/Vl4dimirz/insightforge

Feed it data (uploads or scraped from the web), it cleans and analyzes it,
turns the numbers into plain-language insights with AI, serves everything over a
clean REST API, and exports polished reports — with a dashboard on top.

Built as a focused, production-style showcase of modern Python: **FastAPI**,
**Pydantic**, **pandas**, web scraping, the **Gemini** API, and report
automation.

## Roadmap

- [x] **Phase 1 — API core.** FastAPI service, Pydantic models, AI text endpoint, auto Swagger docs, health check.
- [x] **Phase 2 — Data module.** Upload CSV/Excel → clean → profile with pandas (rows/cols, dtypes, missing values, uniqueness, samples, numeric stats).
- [x] **Phase 3 — Web scraping.** Pull a page summary (BeautifulSoup) or scrape the first table straight into the analyzer (scrape → pandas profile).
- [x] **Phase 4 — AI insights.** Profile (file or scraped) → Gemini → narrative business analysis (overview, findings, data quality, next steps) + optional question.
- [x] **Phase 5 — Dashboard.** Streamlit frontend (`dashboard.py`) that consumes the API: upload/scrape → metrics + profile table + charts → one-click AI insights.
- [x] **Phase 6 — Reports + automation.** Download Excel (`/report/excel`) or a polished PDF with AI analysis (`/report/pdf`); APScheduler runs background jobs on an interval (`/automation/status`, `/automation/run-now`).
- [ ] Phase 7 — Polish, tests, deploy.

## Run it

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # then paste your Gemini key into .env
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs** for interactive API docs.

## Tech

Python · FastAPI · Pydantic · Uvicorn · Google Gemini · (pandas / scraping / reporting — incoming)
