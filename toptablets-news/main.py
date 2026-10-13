"""
main.py - Master CLI Orchestrator for TopTablets.in News Automation System.
Executes individual stages or full autonomous pipeline runs.
"""
import sys
import os
import argparse
import logging

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE_DIR = os.path.dirname(__file__)
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from db import NewsDatabase
import fetch_rss
import filter_tablet_news
import deduplicate
import research_story
import generate_article
import validate_article
import publish_wordpress

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
logger = logging.getLogger("main")


def print_status():
    db = NewsDatabase()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, count(*) as cnt FROM stories GROUP BY status ORDER BY cnt DESC")
        rows = cursor.fetchall()
        cursor.execute("SELECT count(*) as total_topics FROM topics")
        topics_count = cursor.fetchone()["total_topics"]

    print("\n" + "=" * 50)
    print(" 📰 TOPTABLETS.IN NEWS PIPELINE STATUS")
    print("=" * 50)
    print(f"Total Clustered Topics: {topics_count}")
    print("-" * 50)
    total_stories = 0
    for r in rows:
        total_stories += r["cnt"]
        print(f"  • {r['status']:<22}: {r['cnt']} stories")
    print("-" * 50)
    print(f"Total Discovered Stories: {total_stories}")
    print("=" * 50 + "\n")


def run_pipeline(limit: int = 3):
    logger.info(">>> STEP 1: Discovering RSS Feeds...")
    fetch_rss.run_discovery()

    logger.info(">>> STEP 2: Filtering Tablet Relevance...")
    filter_tablet_news.filter_discovered_stories(limit=500)

    logger.info(">>> STEP 3: Deduplicating & Clustering Topics...")
    deduplicate.deduplicate_stories()

    logger.info(f">>> STEP 4: Deep Researching up to {limit} Stories...")
    research_story.research_pending_stories(limit=limit)

    logger.info(f">>> STEP 5: Generating Editorial Drafts for up to {limit} Stories...")
    generate_article.draft_verified_stories(limit=limit)

    logger.info(">>> STEP 6: Auditing Fact Quality & SEO...")
    validate_article.run_quality_audit(limit=limit)

    logger.info(f">>> STEP 7: Publishing Approved Drafts to WordPress (limit={limit})...")
    publish_wordpress.publish_approved_stories(limit=limit)

    logger.info(">>> Pipeline run completed successfully!")
    print_status()


def main():
    parser = argparse.ArgumentParser(description="TopTablets.in AI News Automation Engine")
    subparsers = parser.add_subparsers(dest="command", help="Pipeline Stage Command")

    subparsers.add_parser("discover", help="Discover stories from RSS feeds")
    subparsers.add_parser("filter", help="Filter for consumer tablet relevance")
    subparsers.add_parser("deduplicate", help="Cluster announcements into topics")

    p_res = subparsers.add_parser("research", help="Extract content and build fact sheets")
    p_res.add_argument("--limit", type=int, default=5, help="Number of stories to research")

    p_draft = subparsers.add_parser("draft", help="Generate article drafts")
    p_draft.add_argument("--limit", type=int, default=3, help="Number of drafts to generate")

    subparsers.add_parser("validate", help="Run quality and fact audit")

    p_pub = subparsers.add_parser("publish", help="Publish approved drafts to WordPress")
    p_pub.add_argument("--limit", type=int, default=2, help="Number of drafts to publish")

    p_all = subparsers.add_parser("run-all", help="Execute complete pipeline end-to-end")
    p_all.add_argument("--limit", type=int, default=3, help="Max stories to process in this run")

    subparsers.add_parser("status", help="View current pipeline status counts")

    args = parser.parse_args()

    if args.command == "discover":
        fetch_rss.run_discovery()
    elif args.command == "filter":
        filter_tablet_news.filter_discovered_stories()
    elif args.command == "deduplicate":
        deduplicate.deduplicate_stories()
    elif args.command == "research":
        research_story.research_pending_stories(limit=args.limit)
    elif args.command == "draft":
        generate_article.draft_verified_stories(limit=args.limit)
    elif args.command == "validate":
        validate_article.run_quality_audit()
    elif args.command == "publish":
        publish_wordpress.publish_approved_stories(limit=args.limit)
    elif args.command == "run-all":
        run_pipeline(limit=args.limit)
    elif args.command == "status":
        print_status()
    else:
        print_status()
        parser.print_help()


if __name__ == "__main__":
    main()
