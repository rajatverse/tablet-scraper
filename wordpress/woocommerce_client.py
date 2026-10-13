"""
woocommerce_client.py - Publishes combined tablet products to WooCommerce via REST API.
Creates External/Affiliate products with pricing, attributes, images, and comparison cards.
"""
import re
import requests
import urllib.parse
from typing import Dict, Any, Optional, List
from config import (
    WP_SITE_URL,
    WC_CONSUMER_KEY,
    WC_CONSUMER_SECRET,
    WP_USERNAME,
    WP_APP_PASSWORD,
    WC_POST_STATUS,
    WC_DEFAULT_CATEGORY,
)
from wordpress.product_template import build_full_description, build_short_description


def format_clean_title(tablet: Dict[str, Any]) -> str:
    """Format clean core product title without hardcoded variant parameters."""
    specs = tablet.get("specs") or {}
    model_name = specs.get("model_name") or tablet.get("title", "Tablet")
    if "mini" in model_name.lower():
        return "Apple iPad mini (7th Gen, A17 Pro)"
    # Strip trailing bracketed variant specs like (8.3 Inch, 128 GB, Wi-Fi)
    clean = re.sub(r"\s*\([^)]*(?:GB|TB|Inch|Wi-Fi|Cellular|5G|LTE)[^)]*\)", "", model_name, flags=re.IGNORECASE).strip()
    return clean or model_name


class WooCommerceClient:
    def __init__(self):
        self.site_url = WP_SITE_URL.rstrip("/")
        self.api_base = f"{self.site_url}/wp-json/wc/v3"
        self.auth = self._determine_auth()
        self.category_cache: Dict[str, int] = {}

    def _determine_auth(self):
        if WC_CONSUMER_KEY and WC_CONSUMER_SECRET:
            return (WC_CONSUMER_KEY, WC_CONSUMER_SECRET)
        if WP_USERNAME and WP_APP_PASSWORD:
            return (WP_USERNAME, WP_APP_PASSWORD)
        return None

    def is_configured(self) -> bool:
        return bool(self.site_url and self.auth)

    def test_connection(self) -> Dict[str, Any]:
        """Test API connectivity to WooCommerce."""
        if not self.is_configured():
            return {
                "success": False,
                "error": "WP_SITE_URL and WooCommerce credentials (or Application Password) are not configured."
            }

        url = f"{self.api_base}/system_status"
        try:
            resp = requests.get(url, auth=self.auth, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "site_title": data.get("environment", {}).get("site_title", "WordPress Site"),
                    "wc_version": data.get("environment", {}).get("version", "Unknown"),
                }
            elif resp.status_code == 401 or resp.status_code == 403:
                return {
                    "success": False,
                    "error": f"Authentication failed (HTTP {resp.status_code}). Check your Consumer Key/Secret or Application Password."
                }
            else:
                # Try products endpoint in case system_status permissions are restricted
                prod_resp = requests.get(f"{self.api_base}/products", auth=self.auth, params={"per_page": 1}, timeout=12)
                if prod_resp.status_code in [200, 201]:
                    return {"success": True, "note": "Connection verified via products endpoint."}
                return {
                    "success": False,
                    "error": f"Unexpected response HTTP {resp.status_code}: {resp.text[:200]}"
                }
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}

    def get_or_create_category(self, category_name: str = WC_DEFAULT_CATEGORY) -> Optional[int]:
        """Find or create product category."""
        if category_name in self.category_cache:
            return self.category_cache[category_name]

        url = f"{self.api_base}/products/categories"
        try:
            # Check existing
            resp = requests.get(url, auth=self.auth, params={"search": category_name}, timeout=12)
            if resp.status_code == 200:
                for cat in resp.json():
                    if cat.get("name", "").lower() == category_name.lower():
                        self.category_cache[category_name] = cat["id"]
                        return cat["id"]

            # Create new category
            create_resp = requests.post(url, auth=self.auth, json={"name": category_name}, timeout=12)
            if create_resp.status_code in [200, 201]:
                cat_id = create_resp.json()["id"]
                self.category_cache[category_name] = cat_id
                return cat_id
        except Exception:
            pass
        return None

    def build_payload(self, tablet: Dict[str, Any]) -> Dict[str, Any]:
        """Construct WooCommerce external/affiliate product payload."""
        specs = tablet.get("specs") or {}
        cat_id = self.get_or_create_category(WC_DEFAULT_CATEGORY)

        # Build Attributes list for WooCommerce specs tab
        attributes = []
        spec_fields = [
            ("Brand", specs.get("brand")),
            ("Screen Size", specs.get("screen_size")),
            ("Storage", specs.get("storage")),
            ("RAM", specs.get("ram")),
            ("Processor", specs.get("processor")),
            ("Operating System", specs.get("operating_system")),
            ("Connectivity", specs.get("connectivity")),
            ("Battery", specs.get("battery")),
            ("Color", specs.get("color")),
        ]
        for name, val in spec_fields:
            if val:
                attributes.append({
                    "name": name,
                    "visible": True,
                    "variation": False,
                    "options": [str(val)],
                })

        # Pricing
        best_price = tablet.get("best_price")
        regular_price = tablet.get("regular_price")

        regular_price_str = f"{int(regular_price)}" if regular_price else ""
        sale_price_str = f"{int(best_price)}" if best_price and regular_price and best_price < regular_price else ""

        # Images (Limit to 5 distinctive angles)
        image_payload = []
        for img_url in (tablet.get("images") or [])[:5]:
            if img_url and img_url.startswith("http"):
                image_payload.append({"src": img_url})

        aff_url = tablet.get("primary_aff_url") or ""
        button_text = "Buy on Flipkart ↗" if "flipkart" in aff_url.lower() else "Buy on Amazon ↗"

        payload = {
            "name": format_clean_title(tablet),
            "type": "external",
            "status": WC_POST_STATUS,
            "external_url": aff_url,
            "button_text": button_text,
            "regular_price": regular_price_str,
            "description": build_full_description(tablet),
            "short_description": build_short_description(tablet),
            "attributes": attributes,
        }

        payload["sale_price"] = sale_price_str

        if cat_id:
            payload["categories"] = [{"id": cat_id}]

        if image_payload:
            payload["images"] = image_payload

        return payload

    def publish_tablet(self, tablet: Dict[str, Any], existing_wc_id: Optional[int] = None) -> Dict[str, Any]:
        """Create or update a WooCommerce tablet product."""
        if not self.is_configured():
            return {
                "success": False,
                "error": "WooCommerce REST API is not configured in .env."
            }

        payload = self.build_payload(tablet)

        try:
            if existing_wc_id:
                # Update existing product
                url = f"{self.api_base}/products/{existing_wc_id}"
                resp = requests.put(url, auth=self.auth, json=payload, timeout=25)
            else:
                # Create new product
                url = f"{self.api_base}/products"
                resp = requests.post(url, auth=self.auth, json=payload, timeout=25)

            if resp.status_code in [200, 201]:
                res_data = resp.json()
                return {
                    "success": True,
                    "wc_product_id": res_data.get("id"),
                    "permalink": res_data.get("permalink"),
                    "status": res_data.get("status"),
                }
            else:
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "error": resp.text[:300],
                }
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
