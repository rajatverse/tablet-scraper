"""
storage/db.py - SQLite database management for raw HTML, parsed listings, and combined tablets.
"""
import sqlite3
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from config import DB_PATH, RAW_HTML_DIR
from matcher.matcher import generate_match_key, build_combined_tablet


class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = str(db_path)
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Table for raw HTML archives
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                product_id TEXT,
                url TEXT,
                file_path TEXT,
                raw_html TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Table for individual retail listings (Amazon / Flipkart)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                product_id TEXT,
                url TEXT,
                title TEXT,
                brand TEXT,
                price REAL,
                mrp REAL,
                rating REAL,
                review_count INTEGER,
                match_key TEXT,
                main_image TEXT,
                data_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(platform, product_id)
            )
            """)

            # Table for matched combined tablets
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tablets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_key TEXT UNIQUE,
                title TEXT,
                brand TEXT,
                amazon_listing_id INTEGER,
                flipkart_listing_id INTEGER,
                best_price REAL,
                regular_price REAL,
                best_store TEXT,
                combined_json TEXT,
                wc_product_id INTEGER,
                wc_sync_status TEXT DEFAULT 'not_synced',
                wc_synced_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (amazon_listing_id) REFERENCES listings(id),
                FOREIGN KEY (flipkart_listing_id) REFERENCES listings(id)
            )
            """)

            # Ensure last_price_checked column exists in both tables
            try:
                cursor.execute("ALTER TABLE listings ADD COLUMN last_price_checked TIMESTAMP")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE tablets ADD COLUMN last_price_checked TIMESTAMP")
            except Exception:
                pass

            conn.commit()

    def save_raw_page(self, platform: str, raw_html: str, product_id: Optional[str] = None, url: Optional[str] = None, file_path: Optional[str] = None) -> int:
        """Archive raw HTML."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO raw_pages (platform, product_id, url, file_path, raw_html)
            VALUES (?, ?, ?, ?, ?)
            """, (platform, product_id, url, file_path, raw_html))
            conn.commit()
            return cursor.lastrowid

    def save_listing(self, parsed: Dict[str, Any]) -> int:
        """Save or update a parsed listing (Amazon or Flipkart)."""
        platform = parsed.get("platform", "unknown")
        product_id = parsed.get("product_id") or parsed.get("asin") or parsed.get("fsn")
        title = parsed.get("title")
        brand = (parsed.get("specs") or {}).get("brand") or parsed.get("brand_line")
        price = parsed.get("price_inr")
        mrp = parsed.get("mrp_inr")
        rating = parsed.get("rating")
        review_count = parsed.get("review_count")
        url = parsed.get("url")
        main_image = parsed.get("image")
        match_key = generate_match_key(parsed)
        data_json = json.dumps(parsed, ensure_ascii=False)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO listings (platform, product_id, url, title, brand, price, mrp, rating, review_count, match_key, main_image, data_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(platform, product_id) DO UPDATE SET
                url=excluded.url,
                title=excluded.title,
                brand=excluded.brand,
                price=excluded.price,
                mrp=excluded.mrp,
                rating=excluded.rating,
                review_count=excluded.review_count,
                match_key=excluded.match_key,
                main_image=excluded.main_image,
                data_json=excluded.data_json,
                updated_at=CURRENT_TIMESTAMP
            """, (platform, product_id, url, title, brand, price, mrp, rating, review_count, match_key, main_image, data_json))
            conn.commit()

            cursor.execute("SELECT id FROM listings WHERE platform=? AND product_id=?", (platform, product_id))
            row = cursor.fetchone()
            listing_id = row["id"] if row else cursor.lastrowid

        # Automatically trigger/update matching for this tablet
        self.sync_tablet_match(match_key)
        return listing_id

    def sync_tablet_match(self, match_key: str):
        """Match Amazon & Flipkart listings sharing the same match_key and update tablets table."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM listings WHERE match_key = ?", (match_key,))
            rows = cursor.fetchall()

            if not rows:
                return

            amazon_row = None
            flipkart_row = None

            for r in rows:
                if r["platform"] == "amazon":
                    amazon_row = r
                elif r["platform"] == "flipkart":
                    flipkart_row = r

            amz_data = json.loads(amazon_row["data_json"]) if amazon_row else None
            fk_data = json.loads(flipkart_row["data_json"]) if flipkart_row else None

            combined = build_combined_tablet(amz_data, fk_data)
            combined_json = json.dumps(combined, ensure_ascii=False)

            cursor.execute("""
            INSERT INTO tablets (
                match_key, title, brand, amazon_listing_id, flipkart_listing_id,
                best_price, regular_price, best_store, combined_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(match_key) DO UPDATE SET
                title=excluded.title,
                brand=excluded.brand,
                amazon_listing_id=excluded.amazon_listing_id,
                flipkart_listing_id=excluded.flipkart_listing_id,
                best_price=excluded.best_price,
                regular_price=excluded.regular_price,
                best_store=excluded.best_store,
                combined_json=excluded.combined_json,
                updated_at=CURRENT_TIMESTAMP
            """, (
                match_key,
                combined["title"],
                combined["brand"],
                amazon_row["id"] if amazon_row else None,
                flipkart_row["id"] if flipkart_row else None,
                combined["best_price"],
                combined["regular_price"],
                combined["best_store"],
                combined_json
            ))
            conn.commit()

    def get_all_tablets(self) -> List[Dict[str, Any]]:
        """Fetch all matched combined tablets."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tablets ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_tablet_by_id(self, tablet_id: int) -> Optional[Dict[str, Any]]:
        """Fetch tablet by primary key."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tablets WHERE id = ?", (tablet_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_listings(self) -> List[Dict[str, Any]]:
        """Fetch all individual store listings."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM listings ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def update_wc_sync(self, tablet_id: int, wc_product_id: int, status: str = "synced"):
        """Record successful WooCommerce sync."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE tablets
            SET wc_product_id = ?, wc_sync_status = ?, wc_synced_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (wc_product_id, status, tablet_id))
            conn.commit()

    def get_listing_by_product_id(self, platform: str, product_id: str) -> Optional[Dict[str, Any]]:
        """Find an existing store listing by platform and product ID (ASIN / FSN)."""
        if not platform or not product_id:
            return None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM listings WHERE platform = ? AND product_id = ?", (platform, product_id))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_tablet_by_match_key(self, match_key: str) -> Optional[Dict[str, Any]]:
        """Find an existing matched tablet by its normalized match key."""
        if not match_key:
            return None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tablets WHERE match_key = ?", (match_key,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_tablet_by_listing_id(self, listing_id: int) -> Optional[Dict[str, Any]]:
        """Find the combined tablet associated with an Amazon or Flipkart listing ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM tablets WHERE amazon_listing_id = ? OR flipkart_listing_id = ?",
                (listing_id, listing_id)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_listings_due_for_price_check(self, interval_days: float = 3.0) -> List[Dict[str, Any]]:
        """
        Fetch listings that need a price check.
        A listing is due if:
        1. It has never had a price check (last_price_checked IS NULL), OR
        2. More than `interval_days` (default 3.0) have elapsed since last_price_checked.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM listings
            WHERE url IS NOT NULL AND url != ''
              AND (
                last_price_checked IS NULL
                OR (julianday('now') - julianday(last_price_checked)) >= ?
              )
            ORDER BY COALESCE(last_price_checked, '1970-01-01') ASC
            """, (interval_days,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def update_listing_price(self, listing_id: int, new_price: Optional[float], new_mrp: Optional[float]) -> bool:
        """Update price and MRP for a listing, updating data_json and timestamps."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data_json, match_key FROM listings WHERE id = ?", (listing_id,))
            row = cursor.fetchone()
            if not row:
                return False

            match_key = row["match_key"]
            try:
                data = json.loads(row["data_json"]) if row["data_json"] else {}
            except Exception:
                data = {}

            data["price_inr"] = new_price
            if new_mrp is not None:
                data["mrp_inr"] = new_mrp

            new_json = json.dumps(data, ensure_ascii=False)

            cursor.execute("""
            UPDATE listings
            SET price = ?, mrp = ?, data_json = ?, updated_at = CURRENT_TIMESTAMP, last_price_checked = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (new_price, new_mrp, new_json, listing_id))
            conn.commit()

        # Re-sync tablet comparison pricing
        if match_key:
            self.sync_tablet_match(match_key)
        return True

    def mark_listing_price_checked(self, listing_id: int):
        """Mark a listing as checked without modifying prices (used when price is unchanged)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE listings
            SET last_price_checked = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (listing_id,))
            conn.commit()

