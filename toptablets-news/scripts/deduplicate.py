"""
deduplicate.py - Clusters identical announcements across different publishers into unified Topics.
Prevents publishing multiple competing articles about the same tablet launch.
"""
import os
import re
import json
import logging
from typing import Dict, Any, List, Set
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
logger = logging.getLogger("deduplicate")


def extract_topic_tokens(headline: str) -> Set[str]:
    """Extract core entity and device tokens from headline for clustering."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", headline.lower())
    tokens = cleaned.split()
    stopwords = {
        "and", "the", "in", "with", "for", "to", "at", "a", "an", "is", "of", "on",
        "starts", "starting", "features", "featuring", "announced", "announces",
        "launched", "launches", "launch", "price", "india", "rs", "tablets", "tablet",
        "new", "debuts", "debut", "soon", "ahead", "revealed", "everything", "we", "know"
    }
    return {t for t in tokens if t not in stopwords and len(t) > 1}


def compute_similarity(tokens1: Set[str], tokens2: Set[str]) -> float:
    """Jaccard similarity between two sets of topic tokens."""
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / len(union)


def generate_device_key(brand: str, headline: str) -> str:
    """Generate a clean slug identifier for a topic."""
    brand_clean = (brand or "tablet").lower().strip()
    headline_clean = re.sub(r"[^a-zA-Z0-9\s]", "", headline.lower())
    words = headline_clean.split()
    # Find model words
    model_words = [w for w in words if w not in {"in", "india", "launches", "launched", "starting", "at", "with", "price"}]
    slug = "_".join(model_words[:4])
    return f"{brand_clean}:{slug}"


def deduplicate_stories() -> Dict[str, int]:
    db = NewsDatabase()
    qualified_stories = db.get_stories_by_status("qualified", limit=200)

    logger.info(f"Deduplicating {len(qualified_stories)} qualified stories...")

    clusters: List[List[Dict[str, Any]]] = []

    for story in qualified_stories:
        headline = story["headline"]
        tokens = extract_topic_tokens(headline)
        brand = story["brand"] or ""

        matched_cluster = None
        for cluster in clusters:
            lead_story = cluster[0]
            lead_tokens = extract_topic_tokens(lead_story["headline"])
            lead_brand = lead_story["brand"] or ""

            # Same brand and high token overlap -> same announcement
            if brand and lead_brand and brand.lower() == lead_brand.lower():
                similarity = compute_similarity(tokens, lead_tokens)
                if similarity >= 0.35:
                    matched_cluster = cluster
                    break

        if matched_cluster is not None:
            matched_cluster.append(story)
        else:
            clusters.append([story])

    created_topics = 0
    grouped_duplicates = 0

    with db.get_connection() as conn:
        cursor = conn.cursor()

        for cluster in clusters:
            primary_story = cluster[0]
            headline = primary_story["headline"]
            brand = primary_story["brand"] or "Tablet"
            story_type = primary_story["story_type"] or "product_launch"
            device_key = generate_device_key(brand, headline)

            # Check if topic already exists
            cursor.execute("SELECT id FROM topics WHERE device_key = ?", (device_key,))
            existing_topic = cursor.fetchone()

            if existing_topic:
                topic_id = existing_topic["id"]
            else:
                cursor.execute("""
                INSERT INTO topics (canonical_title, device_key, story_type, primary_story_id, status)
                VALUES (?, ?, ?, ?, 'research_pending')
                """, (headline, device_key, story_type, primary_story["id"]))
                topic_id = cursor.lastrowid
                created_topics += 1

            # Update primary story
            db.update_story_status(
                story_id=primary_story["id"],
                new_status="research_pending",
                stage="deduplication",
                details=f"Assigned as primary story for topic #{topic_id} ({device_key})",
                extra_fields={"topic_id": topic_id},
                conn=conn
            )

            # Update secondary stories as duplicate_grouped
            for secondary in cluster[1:]:
                db.update_story_status(
                    story_id=secondary["id"],
                    new_status="duplicate_grouped",
                    stage="deduplication",
                    details=f"Grouped into topic #{topic_id} (duplicate of story #{primary_story['id']})",
                    extra_fields={"topic_id": topic_id},
                    conn=conn
                )
                grouped_duplicates += 1

    logger.info(f"[Deduplication Complete] Created {created_topics} Topics, Grouped {grouped_duplicates} duplicate stories.")
    return {"created_topics": created_topics, "grouped_duplicates": grouped_duplicates}


if __name__ == "__main__":
    deduplicate_stories()
