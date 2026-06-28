"""
The scraping layer — fetch a web page and pull structured data out of it.

Two jobs:
  • scrape_page(url)  → a summary of the page (title, description, headings, link/
    image counts, a text preview). Uses BeautifulSoup to walk the HTML.
  • scrape_table(url) → find the first HTML <table> and hand it back as a pandas
    DataFrame, so it flows straight into the Phase 2 analyzer. Scrape → analyze.
"""

import io

import requests
import pandas as pd
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; InsightForge/1.0; +data-tool)"}
TIMEOUT = 15


class ScrapeError(ValueError):
    """Raised when a page can't be fetched or parsed."""


def fetch_html(url: str) -> str:
    if not url or not url.lower().startswith(("http://", "https://")):
        raise ScrapeError("Enter a full URL starting with http:// or https://")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise ScrapeError(f"Couldn't fetch that page: {e}") from e
    return resp.text


def scrape_page(url: str) -> dict:
    """Summarize a page's structure and content."""
    soup = BeautifulSoup(fetch_html(url), "lxml")

    title = soup.title.get_text(strip=True) if soup.title else ""

    desc_tag = soup.find("meta", attrs={"name": "description"})
    description = desc_tag.get("content", "").strip() if desc_tag else ""

    headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2"])]
    headings = [h for h in headings if h][:20]

    links = soup.find_all("a", href=True)
    images = soup.find_all("img")
    tables = soup.find_all("table")

    # Plain text, with the noise stripped out.
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ").split())

    return {
        "url": url,
        "title": title,
        "description": description,
        "headings": headings,
        "links_count": len(links),
        "images_count": len(images),
        "tables_count": len(tables),
        "text_chars": len(text),
        "text_preview": text[:500],
    }


def scrape_table(url: str) -> pd.DataFrame:
    """Extract the first HTML table on the page as a DataFrame (pandas does the parsing)."""
    try:
        tables = pd.read_html(io.StringIO(fetch_html(url)))
    except ValueError as e:  # pandas raises ValueError when it finds no tables
        raise ScrapeError(f"No tables found on that page ({e}).") from e
    if not tables:
        raise ScrapeError("No tables found on that page.")
    return tables[0]
