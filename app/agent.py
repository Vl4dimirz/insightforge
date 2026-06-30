"""
The autonomous research agent — InsightForge's headline capability.

Give it a goal in plain English plus a few URLs, and it runs the whole loop
itself, no step-by-step babysitting:

    PLAN       → decide which dimensions to investigate for this goal
    GATHER     → scrape each page (resilient: a bad URL is noted, not fatal)
    SYNTHESIZE → write one grounded, comparative report from everything gathered

It's the scrape + AI layers wired into a single agent. To stay friendly to
Gemini's free-tier quota, the whole run is just two model calls (plan +
synthesize) on the lighter, higher-quota flash-lite model; scraping is free.
"""

from app.ai import generate, AIError
from app.scrape import scrape_page, ScrapeError

# flash-lite has a much larger free daily quota than flash — right for an agent
# that makes several calls and may run many times a day.
AGENT_MODEL = "gemini-2.5-flash-lite"

MAX_URLS = 5

PLAN_PROMPT = """You are a research analyst. You are about to examine several web pages to address this goal:

GOAL: {goal}

List 3 to 5 specific dimensions you will compare the pages on (e.g. "pricing clarity", "product range", "trust signals"). One per line, a few words each. No numbering, no extra commentary."""

SYNTH_PROMPT = """You are a senior analyst writing a grounded report. Address this goal:

GOAL: {goal}

You examined the web pages below. Here is the structured data gathered from each:

{sources_block}

Compare them on these dimensions: {focus}

Write a tight, practical report with these sections:
1. Summary — what these pages are and how they compare at a glance.
2. Per-source notes — for EACH source, its strengths and weaknesses, grounded in the gathered data.
3. Comparison — how they stack up across the dimensions above.
4. Recommendations — 3 concrete, actionable next steps for the goal.

Ground every claim in the gathered data. Never invent specifics (numbers, features, prices) that aren't present in the data."""


def _plan(goal: str) -> list[str]:
    """One model call: turn the goal into a short list of comparison dimensions."""
    raw = generate(PLAN_PROMPT.format(goal=goal), model=AGENT_MODEL)
    dims: list[str] = []
    for line in raw.splitlines():
        line = line.strip().lstrip("-*0123456789. ").strip()
        if line:
            dims.append(line)
    return dims[:5] or ["overall quality", "strengths", "weaknesses"]


def _gather(urls: list[str]) -> tuple[list[dict], list[dict]]:
    """Scrape each URL. Returns (sources, step_log). A failed page is recorded,
    not fatal — the agent keeps going with what it can get."""
    sources: list[dict] = []
    steps: list[dict] = []
    for url in urls:
        try:
            page = scrape_page(url)
            sources.append(page)
            steps.append({"phase": "gather", "summary": f"Scraped {url}", "detail": page["title"] or "(no title)"})
        except ScrapeError as e:
            sources.append({"url": url, "error": str(e)})
            steps.append({"phase": "gather", "summary": f"Could not scrape {url}", "detail": str(e)})
    return sources, steps


def _sources_block(sources: list[dict]) -> str:
    """Render the gathered pages into a compact block for the synthesis prompt."""
    blocks = []
    for i, s in enumerate(sources, 1):
        if s.get("error"):
            blocks.append(f"[{i}] {s['url']} — could not be fetched ({s['error']}).")
            continue
        headings = ", ".join(s.get("headings", [])[:12]) or "(none)"
        blocks.append(
            f"[{i}] {s['url']}\n"
            f"    Title: {s.get('title') or '(none)'}\n"
            f"    Description: {s.get('description') or '(none)'}\n"
            f"    Headings: {headings}\n"
            f"    Links: {s.get('links_count', 0)} | Images: {s.get('images_count', 0)} | Tables: {s.get('tables_count', 0)}\n"
            f"    Text preview: {s.get('text_preview', '')}"
        )
    return "\n\n".join(blocks)


def _synthesize(goal: str, focus: list[str], sources: list[dict]) -> str:
    """One model call: write the full comparative report from everything gathered."""
    prompt = SYNTH_PROMPT.format(
        goal=goal,
        sources_block=_sources_block(sources),
        focus=", ".join(focus),
    )
    return generate(prompt, model=AGENT_MODEL)


def run_agent(goal: str, urls: list[str]) -> dict:
    """Run the full plan → gather → synthesize loop and return a transparent result."""
    goal = (goal or "").strip()
    if not goal:
        raise ValueError("Give the agent a goal — what should it find out?")
    urls = [u.strip() for u in (urls or []) if u and u.strip()][:MAX_URLS]
    if not urls:
        raise ValueError("Give the agent at least one URL to investigate.")

    steps: list[dict] = []

    # 1) PLAN
    focus = _plan(goal)
    steps.append({"phase": "plan", "summary": f"Planned {len(focus)} focus dimensions", "detail": ", ".join(focus)})

    # 2) GATHER
    sources, gather_steps = _gather(urls)
    steps.extend(gather_steps)
    if all(s.get("error") for s in sources):
        raise ScrapeError("None of the URLs could be fetched, so there was nothing to analyze.")

    # 3) SYNTHESIZE
    report = _synthesize(goal, focus, sources)
    steps.append({"phase": "synthesize", "summary": "Wrote the comparative report", "detail": f"{len(report)} characters"})

    return {"goal": goal, "focus": focus, "steps": steps, "sources": sources, "report": report}
