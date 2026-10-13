"""
filter_tablet_news.py - Heuristic filtering and categorization for discovered stories.
Separates real consumer tablet news from unrelated articles (pharma, graphics tablets, accessories).
"""
import os
import re
import json
import logging
from typing import Dict, Any, List, Tuple
from db import NewsDatabase

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
KEYWORDS_FILE = os.path.join(BASE_DIR, "config", "tablet_keywords.json")
LOG_DIR = os.path.join(BASE_DIR, "data", "logs")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "pipeline.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("filter_news")


def load_keywords() -> Dict[str, Any]:
    with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def check_exclusions(text: str, exclusions: List[str]) -> Tuple[bool, str]:
    text_lower = text.lower()
    for exc in exclusions:
        pattern = r"\b" + re.escape(exc) + r"\b"
        if re.search(pattern, text_lower):
            return True, exc
    return False, ""


def detect_tablet_relevance(text: str, keywords: Dict[str, Any]) -> Tuple[bool, str, List[str]]:
    text_lower = text.lower()
    detected_devices = []
    detected_brand = ""

    # Check series names first
    for series in keywords.get("series_names", []):
        if series in text_lower:
            detected_devices.append(series.title())

    # Check brand + tablet combo
    for brand in keywords.get("major_brands", []):
        if re.search(r"\b" + re.escape(brand) + r"\b", text_lower):
            if not detected_brand:
                detected_brand = brand.title()
            for ff in keywords.get("target_form_factors", []):
                if re.search(r"\b" + re.escape(ff) + r"\b", text_lower):
                    detected_devices.append(f"{brand.title()} {ff.title()}")

    is_relevant = len(detected_devices) > 0 or ("ipad" in text_lower) or ("tablet" in text_lower)
    return is_relevant, detected_brand, list(set(detected_devices))


def detect_india_relevance(text: str, keywords: Dict[str, Any]) -> bool:
    text_lower = text.lower()
    for kw in keywords.get("india_relevance_keywords", []):
        if kw in text_lower:
            return True
    return False


def detect_story_type(text: str, keywords: Dict[str, Any]) -> str:
    text_lower = text.lower()
    signals = keywords.get("story_type_signals", {})
    for stype, triggers in signals.items():
        for tr in triggers:
            if tr in text_lower:
                return stype
    return "product_launch"


def filter_discovered_stories(limit: int = 100) -> Dict[str, int]:
    db = NewsDatabase()
    keywords = load_keywords()
    stories = db.get_stories_by_status("discovered", limit=limit)

    qualified_count = 0
    rejected_count = 0

    logger.info(f"Filtering {len(stories)} discovered stories...")

    for story in stories:
        story_id = story["id"]
        headline = story["headline"] or ""
        summary = story["raw_summary"] or ""
        full_text = f"{headline} {summary}"

        # 1. Exclusion Check
        is_excluded, exc_word = check_exclusions(full_text, keywords.get("mandatory_exclusions", []))
        if is_excluded:
            db.update_story_status(
                story_id=story_id,
                new_status="rejected",
                stage="filtering",
                details=f"Excluded via keyword: {exc_word}",
                extra_fields={"rejection_reason": f"Excluded keyword '{exc_word}'"}
            )
            rejected_count += 1
            continue

        # 2. Tablet Relevance
        is_tablet, brand, devices = detect_tablet_relevance(full_text, keywords)
        if not is_tablet:
            db.update_story_status(
                story_id=story_id,
                new_status="rejected",
                stage="filtering",
                details="Not relevant to consumer tablets",
                extra_fields={"rejection_reason": "No tablet keywords found"}
            )
            rejected_count += 1
            continue

        # 3. India Relevance & Story Type
        is_india = detect_india_relevance(full_text, keywords)
        story_type = detect_story_type(full_text, keywords)

        db.update_story_status(
            story_id=story_id,
            new_status="qualified",
            stage="filtering",
            details=f"Qualified as {story_type} (India: {is_india})",
            extra_fields={
                "tablet_relevant": 1,
                "india_relevant": 1 if is_india else 0,
                "brand": brand,
                "device_names": devices,
                "story_type": story_type
            }
        )
        qualified_count += 1

    logger.info(f"[Filtering Complete] Qualified: {qualified_count}, Rejected: {rejected_count}")
    return {"qualified": qualified_count, "rejected": rejected_count}


if __name__ == "__main__":
    filter_discovered_stories()
