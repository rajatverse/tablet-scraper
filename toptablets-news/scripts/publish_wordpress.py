"""
publish_wordpress.py - Publishes quality-passed articles as WordPress drafts via REST API.
Guarantees idempotency: never duplicates posts, stores returned post IDs and URLs.
"""
import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from db import NewsDatabase

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
load_dotenv(os.path.join(ROOT_DIR, ".env"))

LOG_DIR = os.path.join(BASE_DIR, "data", "logs")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "pipeline.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("publish_wordpress")

WP_SITE_URL = os.getenv("WP_SITE_URL", "https://toptablets.in").rstrip("/")
WP_USERNAME = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")


class WordPressPublisher:
    def __init__(self):
        self.api_base = f"{WP_SITE_URL}/wp-json/wp/v2"
        self.session = requests.Session()
        self.nonce = None
        self.auth = (WP_USERNAME, WP_APP_PASSWORD) if WP_USERNAME and WP_APP_PASSWORD else None
        self.tag_cache: Dict[str, int] = {}
        self._authenticate()

    def _authenticate(self):
        """Authenticate via WordPress session to get active REST nonce, or fallback to Basic Auth."""
        if not WP_USERNAME or not WP_APP_PASSWORD:
            return
        try:
            r = self.session.post(
                f"{WP_SITE_URL}/wp-login.php",
                data={"log": WP_USERNAME, "pwd": WP_APP_PASSWORD, "rememberme": "forever", "wp-submit": "Log In"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=12
            )
            if r.status_code == 200:
                r_admin = self.session.get(f"{WP_SITE_URL}/wp-admin/index.php", timeout=12)
                import re
                nonces = re.findall(r'wpApiSettings\s*=\s*\{\s*"root":[^}]*"nonce":"([^"]+)"', r_admin.text)
                if nonces:
                    self.nonce = nonces[0]
                    logger.info("WordPress session authenticated with active REST Nonce.")
        except Exception as e:
            logger.warning(f"Session authentication note: {e}")

    def is_configured(self) -> bool:
        return bool(self.nonce or self.auth)

    def _get_headers(self) -> Dict[str, str]:
        headers = {"User-Agent": "Mozilla/5.0"}
        if self.nonce:
            headers["X-WP-Nonce"] = self.nonce
        return headers

    def get_or_create_tag(self, tag_name: str) -> Optional[int]:
        """Lookup tag ID or create if missing."""
        tag_clean = tag_name.strip()
        if tag_clean in self.tag_cache:
            return self.tag_cache[tag_clean]

        try:
            # Search tag
            r = self.session.get(f"{self.api_base}/tags?search={tag_clean}", auth=None if self.nonce else self.auth, headers=self._get_headers(), timeout=10)
            if r.status_code == 200:
                tags = r.json()
                for t in tags:
                    if t.get("name", "").lower() == tag_clean.lower():
                        self.tag_cache[tag_clean] = t["id"]
                        return t["id"]

            # Create tag if not found
            r_create = self.session.post(f"{self.api_base}/tags", auth=None if self.nonce else self.auth, headers=self._get_headers(), json={"name": tag_clean}, timeout=10)
            if r_create.status_code in [200, 201]:
                t_id = r_create.json().get("id")
                self.tag_cache[tag_clean] = t_id
                return t_id
        except Exception as e:
            logger.debug(f"Tag lookup note for '{tag_clean}': {e}")
        return None

    def publish_draft(self, story: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_configured():
            return {"success": False, "error": "WordPress credentials not configured in .env"}

        article = json.loads(story["article_json"])

        # Tag IDs
        tag_ids = []
        for t_name in (article.get("tags") or []):
            tid = self.get_or_create_tag(t_name)
            if tid:
                tag_ids.append(tid)

        payload = {
            "title": article.get("headline", story["headline"]),
            "slug": article.get("slug", ""),
            "status": "draft",  # Safety: start as draft
            "content": article.get("article_html", ""),
            "excerpt": article.get("excerpt", ""),
            "categories": [1],  # Category 1: News
            "tags": tag_ids,
        }

        try:
            resp = self.session.post(f"{self.api_base}/posts", auth=None if self.nonce else self.auth, headers=self._get_headers(), json=payload, timeout=20)
            if resp.status_code in [200, 201]:
                data = resp.json()
                return {
                    "success": True,
                    "wp_post_id": data.get("id"),
                    "wp_url": data.get("link"),
                    "status": data.get("status")
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {resp.status_code}: {resp.text[:300]}"
                }
        except Exception as ex:
            return {"success": False, "error": str(ex)}


def publish_approved_stories(limit: int = 2) -> int:
    db = NewsDatabase()
    publisher = WordPressPublisher()

    if not publisher.is_configured():
        logger.error("WordPress authentication is not configured.")
        return 0

    approved_stories = db.get_stories_by_status("quality_passed", limit=limit)
    logger.info(f"Publishing up to {limit} approved drafts to WordPress ({WP_SITE_URL})...")

    published_count = 0

    for story in approved_stories:
        story_id = story["id"]
        # Double check: ensure no post already created
        if story.get("wp_post_id"):
            logger.info(f"Story #{story_id} already has WP Post #{story['wp_post_id']}, skipping.")
            continue

        res = publisher.publish_draft(story)
        if res.get("success"):
            wp_id = res.get("wp_post_id")
            wp_link = res.get("wp_url")
            db.update_story_status(
                story_id=story_id,
                new_status="published",
                stage="publishing",
                details=f"Draft created on WordPress: Post ID #{wp_id} ({wp_link})",
                extra_fields={"wp_post_id": wp_id, "wp_url": wp_link}
            )
            published_count += 1
            logger.info(f"Story #{story_id} published to WordPress -> Post ID #{wp_id} ({wp_link})")
        else:
            logger.error(f"Failed to publish Story #{story_id}: {res.get('error')}")

    logger.info(f"[Publishing Complete] Created {published_count} WordPress drafts.")
    return published_count


if __name__ == "__main__":
    publish_approved_stories(limit=1)
