"""
validate_article.py - Automated quality and fact-integrity gatekeeper.
Verifies SEO field constraints, semantic HTML structure, source citations,
and cross-checks all monetary claims against the verified fact sheet.
"""
import os
import re
import json
import logging
from typing import Dict, Any, List, Tuple
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
logger = logging.getLogger("validate_article")


def validate_single_draft(story: Dict[str, Any]) -> Tuple[bool, List[str]]:
    story_id = story["id"]
    errors = []

    if not story.get("article_json"):
        return False, ["Missing article_json payload"]

    article = json.loads(story["article_json"])
    fact_sheet = json.loads(story.get("fact_sheet") or "{}")

    # 1. Required fields
    required_fields = ["headline", "seo_title", "meta_description", "slug", "article_html", "category"]
    for rf in required_fields:
        if not article.get(rf):
            errors.append(f"Missing required field: {rf}")

    # 2. Length & Formatting Constraints
    seo_title = article.get("seo_title", "")
    if len(seo_title) > 80:
        errors.append(f"seo_title too long ({len(seo_title)} chars > 80)")

    meta_desc = article.get("meta_description", "")
    if len(meta_desc) > 175:
        errors.append(f"meta_description too long ({len(meta_desc)} chars > 175)")

    html = article.get("article_html", "")
    if len(html) < 300:
        errors.append(f"article_html too short ({len(html)} chars)")

    if "<table" not in html:
        errors.append("Missing specification table in article_html")

    if "tt-source-citation" not in html and "href=" not in html:
        errors.append("Missing source citation link in article body")

    # 3. Anti-Hallucination Price Verification
    verified_prices = set()
    for f in fact_sheet.get("facts", []):
        if f.get("field") == "starting_price_inr" and f.get("value"):
            verified_prices.add(int(f["value"]))

    article_prices = re.findall(r"(?:₹|Rs\.?|INR)\s*([0-9]{1,2},[0-9]{2,3}(?:,[0-9]{3})?|[0-9]{4,6})", html, flags=re.IGNORECASE)
    for p_str in article_prices:
        val = int(p_str.replace(",", ""))
        # If price looks like a product price (> 3000), check against verified prices
        if val > 3000 and verified_prices and val not in verified_prices:
            # Check if within range or conflict
            errors.append(f"Unverified price ₹{val:,} found in prose (verified: {verified_prices})")

    is_valid = len(errors) == 0
    return is_valid, errors


def run_quality_audit(limit: int = 10) -> Dict[str, int]:
    db = NewsDatabase()
    drafted_stories = db.get_stories_by_status("drafted", limit=limit)

    passed_count = 0
    failed_count = 0

    logger.info(f"Auditing {len(drafted_stories)} drafted stories for quality & factual integrity...")

    for story in drafted_stories:
        story_id = story["id"]
        is_valid, errors = validate_single_draft(story)

        if is_valid:
            db.update_story_status(
                story_id=story_id,
                new_status="quality_passed",
                stage="validation",
                details="All quality & fact integrity checks passed."
            )
            passed_count += 1
            logger.info(f"Story #{story_id} PASSED quality audit.")
        else:
            db.update_story_status(
                story_id=story_id,
                new_status="quality_failed",
                stage="validation",
                details=f"Quality audit failed: {'; '.join(errors)}"
            )
            failed_count += 1
            logger.warning(f"Story #{story_id} FAILED quality audit: {errors}")

    logger.info(f"[Audit Complete] Passed: {passed_count}, Failed: {failed_count}")
    return {"passed": passed_count, "failed": failed_count}


if __name__ == "__main__":
    run_quality_audit()
