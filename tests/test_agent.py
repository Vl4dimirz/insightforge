"""Tests for the autonomous research agent — mocked AI and scraping, so they're
fast, offline, and don't touch the Gemini quota."""

import pytest

import app.agent as agent
from app.scrape import ScrapeError


def _fake_page(url):
    return {
        "url": url,
        "title": f"Title of {url}",
        "description": "A description",
        "headings": ["Overview", "Pricing"],
        "links_count": 10,
        "images_count": 2,
        "tables_count": 0,
        "text_chars": 1234,
        "text_preview": "Some readable preview text about the page.",
    }


@pytest.fixture
def mocked(monkeypatch):
    monkeypatch.setattr(agent, "scrape_page", lambda url: _fake_page(url))
    monkeypatch.setattr(
        agent,
        "generate",
        lambda prompt, model=None: (
            "- pricing\n- features\n- trust"
            if "List 3 to 5 specific dimensions" in prompt
            else "1. Summary\nGrounded report body."
        ),
    )


def test_agent_runs_full_loop(mocked):
    res = agent.run_agent("Compare these", ["https://a.com", "https://b.com"])
    assert res["goal"] == "Compare these"
    assert res["focus"] == ["pricing", "features", "trust"]
    assert len(res["sources"]) == 2
    assert "Grounded report" in res["report"]
    phases = [s["phase"] for s in res["steps"]]
    assert phases == ["plan", "gather", "gather", "synthesize"]


def test_agent_requires_goal_and_urls(mocked):
    with pytest.raises(ValueError):
        agent.run_agent("", ["https://a.com"])
    with pytest.raises(ValueError):
        agent.run_agent("goal", [])


def test_agent_is_resilient_to_a_bad_url(monkeypatch):
    def flaky_scrape(url):
        if "bad" in url:
            raise ScrapeError("boom")
        return _fake_page(url)

    monkeypatch.setattr(agent, "scrape_page", flaky_scrape)
    monkeypatch.setattr(
        agent,
        "generate",
        lambda prompt, model=None: "- x" if "List 3 to 5 specific dimensions" in prompt else "report",
    )

    res = agent.run_agent("goal", ["https://good.com", "https://bad.com"])
    # one good source, one recorded error — the run still completes
    assert any(s.get("error") for s in res["sources"])
    assert any(not s.get("error") for s in res["sources"])
    assert res["report"] == "report"


def test_agent_caps_url_count(mocked):
    many = [f"https://s{i}.com" for i in range(10)]
    res = agent.run_agent("goal", many)
    assert len(res["sources"]) == agent.MAX_URLS
