"""
fetch_rss.py - Discovers tablet news stories from configured RSS feeds.
Parses Google News RSS, manufacturer newsrooms, and tech publication feeds.
"""
import os
import json
import logging
import requests
import feedparser
from typing import Dict, Any, List
from db import NewsDatabase

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SOURCES_FILE = os.path.join(BASE_DIR, "config", "sources.json")
LOG_DIR = os.path.join(BASE_DIR, "data", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "pipeline.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("fetch_rss")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


def decode_google_news_url(url: str) -> str:
    """Attempt to decode Google News redirect URL to original canonical publisher URL."""
    if "news.google.com" not in url:
        return url
    try:
        from googlenewsdecoder import gnewsdecoder
        res = gnewsdecoder(url)
        if res and res.get("decoded_url"):
            return res.get("decoded_url")
    except Exception as e:
        logger.debug(f"Google News decoder note: {e}")
    return url


def load_sources() -> List[Dict[str, Any]]:
    if not os.path.exists(SOURCES_FILE):
        logger.error(f"Sources file not found at {SOURCES_FILE}")
        return []
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("rss_feeds", [])


def fetch_feed_entries(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    name = source.get("name", "Unknown Feed")
    url = source.get("url")
    is_google = source.get("type") == "google_news_rss"
    entries = []

    logger.info(f"Fetching {name} -> {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"Feed {name} responded with status {resp.status_code}")
            return []

        parsed = feedparser.parse(resp.content)
        for e in parsed.entries:
            raw_link = getattr(e, "link", "")
            if not raw_link:
                continue

            headline = getattr(e, "title", "").strip()
            published = getattr(e, "published", "") or getattr(e, "updated", "")
            summary = getattr(e, "summary", "") or getattr(e, "description", "")

            # Extract publisher name from Google News title suffix if applicable
            publisher = name
            if is_google and " - " in headline:
                parts = headline.rsplit(" - ", 1)
                headline = parts[0].strip()
                publisher = parts[1].strip()

            entries.append({
                "guid": getattr(e, "id", raw_link),
                "url": raw_link,
                "decoded_url": None,
                "headline": headline,
                "publisher": publisher,
                "published_date": published,
                "raw_summary": summary,
            })
    except Exception as ex:
        logger.error(f"Error fetching feed {name}: {ex}")

    return entries


def run_discovery() -> Dict[str, int]:
    db = NewsDatabase()
    sources = load_sources()
    total_found = 0
    total_saved = 0

    for src in sources:
        if not src.get("enabled", True):
            continue
        entries = fetch_feed_entries(src)
        total_found += len(entries)
        for item in entries:
            saved_id = db.save_discovered_story(item)
            if saved_id:
                total_saved += 1

    logger.info(f"[RSS Discovery Complete] Discovered {total_found} entries, Saved {total_saved} new stories to DB.")
    return {"total_found": total_found, "total_saved": total_saved}


if __name__ == "__main__":
    run_discovery()
