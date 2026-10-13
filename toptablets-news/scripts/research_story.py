"""
research_story.py - Fetches original source material, extracts clean article text using Trafilatura,
and builds a structured fact-checking record with source citations and conflict detection.
"""
import os
import re
import json
import logging
import requests
import trafilatura
from typing import Dict, Any, List, Optional
from db import NewsDatabase

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOG_DIR = os.path.join(BASE_DIR, "data", "logs")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "pipeline.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("research_story")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
}


def resolve_canonical_url(url: str) -> str:
    """Resolve Google News redirects to the direct publisher URL."""
    if "news.google.com" not in url:
        return url
    try:
        from googlenewsdecoder import gnewsdecoder
        res = gnewsdecoder(url)
        if res and res.get("decoded_url"):
            return res.get("decoded_url")
    except Exception as e:
        logger.debug(f"Decoder fallback: {e}")
    return url


def fetch_and_extract_article(url: str) -> Optional[str]:
    """Fetch article HTML and extract clean text body via Trafilatura."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            extracted = trafilatura.extract(
                resp.text,
                include_comments=False,
                include_tables=True,
                no_fallback=False
            )
            return extracted
    except Exception as ex:
        logger.warning(f"Failed to fetch content from {url}: {ex}")
    return None


def extract_facts_from_text(text: str, source_url: str) -> Dict[str, Any]:
    """Extract key hardware specifications, pricing, and claims from article text."""
    facts = []

    # 1. Starting Price in INR
    prices = re.findall(r"(?:₹|Rs\.?|INR)\s*([0-9]{1,2},[0-9]{2,3}(?:,[0-9]{3})?|[0-9]{4,6})", text, flags=re.IGNORECASE)
    clean_price = None
    if prices:
        # Convert first found price to integer
        val = int(prices[0].replace(",", ""))
        if 4000 <= val <= 250000:
            clean_price = val
            facts.append({
                "field": "starting_price_inr",
                "value": clean_price,
                "display": f"₹{clean_price:,}",
                "source_url": source_url,
                "status": "extracted"
            })

    if not clean_price:
        facts.append({
            "field": "starting_price_inr",
            "value": None,
            "display": "Unconfirmed / TBA",
            "source_url": source_url,
            "status": "unconfirmed"
        })

    # 2. Display Size
    display_match = re.search(r"(\d{1,2}(?:\.\d{1,2})?)\s*(?:-inch|\s*inch|\"|″)\s*(?:IPS|LCD|OLED|AMOLED|display|screen)?", text, flags=re.IGNORECASE)
    if display_match:
        size = float(display_match.group(1))
        if 7.0 <= size <= 15.0:
            facts.append({
                "field": "display_size",
                "value": f"{size} Inch",
                "source_url": source_url,
                "status": "extracted"
            })

    # 3. Processor / Chipset
    soc_match = re.search(r"(Snapdragon\s*[0-9\+Gen\s]+|MediaTek\s*(?:Dimensity|Helio)?\s*[A-Za-z0-9\+]+|Apple\s*A[0-9]+(?:\s*Bionic|\s*Pro)?|Apple\s*M[1-4]|Unisoc\s*T[0-9]+|Exynos\s*[0-9]+)", text, flags=re.IGNORECASE)
    if soc_match:
        facts.append({
            "field": "processor",
            "value": soc_match.group(0).strip(),
            "source_url": source_url,
            "status": "extracted"
        })

    # 4. Battery Capacity
    battery_match = re.search(r"([0-9]{4,5})\s*mAh", text, flags=re.IGNORECASE)
    if battery_match:
        facts.append({
            "field": "battery_capacity",
            "value": f"{battery_match.group(1)} mAh",
            "source_url": source_url,
            "status": "extracted"
        })

    # 5. Connectivity (5G / 4G / Wi-Fi)
    conn = "Wi-Fi"
    if re.search(r"\b5G\b", text, flags=re.IGNORECASE):
        conn = "5G + Wi-Fi"
    elif re.search(r"\b(?:4G|LTE|SIM)\b", text, flags=re.IGNORECASE):
        conn = "4G LTE + Wi-Fi"
    facts.append({
        "field": "connectivity",
        "value": conn,
        "source_url": source_url,
        "status": "extracted"
    })

    return facts


def research_single_story(story_id: int) -> bool:
    db = NewsDatabase()
    story = db.get_story_by_id(story_id)
    if not story:
        return False

    raw_url = story["url"]
    decoded_url = story["decoded_url"] or resolve_canonical_url(raw_url)
    headline = story["headline"]

    logger.info(f"Researching Story #{story_id}: {headline[:60]}... -> {decoded_url}")

    # Fetch primary content
    content = fetch_and_extract_article(decoded_url)
    if not content:
        # Fallback to raw summary if page blocked
        content = story["raw_summary"] or ""
        logger.warning(f"Used summary fallback for Story #{story_id}")

    # Extract facts from primary article
    facts = extract_facts_from_text(content, decoded_url)

    # Cross-check with secondary stories if part of a topic
    conflicts = []
    secondary_sources = []
    topic_id = story["topic_id"]

    if topic_id:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, url, decoded_url FROM stories WHERE topic_id = ? AND id != ?", (topic_id, story_id))
            secondaries = cursor.fetchall()
            for s in secondaries[:2]:  # check up to 2 secondary sources
                s_url = s["decoded_url"] or resolve_canonical_url(s["url"])
                s_content = fetch_and_extract_article(s_url)
                if s_content:
                    secondary_sources.append(s_url)
                    s_facts = extract_facts_from_text(s_content, s_url)
                    # Check for conflicting prices
                    p1 = next((f["value"] for f in facts if f["field"] == "starting_price_inr"), None)
                    p2 = next((f["value"] for f in s_facts if f["field"] == "starting_price_inr"), None)
                    if p1 and p2 and p1 != p2:
                        conflicts.append(f"Price discrepancy: Primary source lists ₹{p1:,}, secondary lists ₹{p2:,}")

    fact_sheet = {
        "headline": headline,
        "story_type": story.get("story_type", "product_launch"),
        "market": "India" if story.get("india_relevant") else "Global / India Expected",
        "primary_source_url": decoded_url,
        "secondary_sources": secondary_sources,
        "facts": facts,
        "unresolved_conflicts": conflicts,
        "extracted_content_length": len(content),
    }

    # Decide next status: verified vs needs_review
    new_status = "verified" if not conflicts else "needs_review"

    db.update_story_status(
        story_id=story_id,
        new_status=new_status,
        stage="research",
        details=f"Extracted {len(facts)} facts from {decoded_url} ({len(content)} chars)",
        extra_fields={
            "decoded_url": decoded_url,
            "content_text": content,
            "fact_sheet": fact_sheet
        }
    )

    logger.info(f"Story #{story_id} status updated to '{new_status}' with {len(facts)} facts.")
    return True


def research_pending_stories(limit: int = 5) -> int:
    db = NewsDatabase()
    pending = db.get_stories_by_status("research_pending", limit=limit)
    logger.info(f"Starting research on {len(pending)} pending stories...")
    count = 0
    for s in pending:
        success = research_single_story(s["id"])
        if success:
            count += 1
    return count


if __name__ == "__main__":
    research_pending_stories(limit=5)
