"""
flipkart_parser.py - Robust parser for Flipkart product pages.

Extracts structured product data from Flipkart HTML page source:
- Title, Brand, Model
- Price, MRP, Discount %
- Rating, Review count, Rating count
- High-res images
- Highlights / Bullets
- Organized Specifications (General, Display, Performance, Battery, etc.)
- Normalized tablet specs
"""
import json
import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from parsers.spec_normalizer import normalize_tablet_specs

FSN_RE = re.compile(r"[?&]pid=([A-Z0-9]{16})", re.IGNORECASE)


class BlockedOrChanged(Exception):
    """Raised when the HTML is blocked or layout is unrecognized."""


def _text(soup: BeautifulSoup, *selectors: str) -> Optional[str]:
    """First non-empty text among fallback selectors."""
    for sel in selectors:
        n = soup.select_one(sel)
        if n:
            val = n.get_text(" ", strip=True)
            if val:
                return val
    return None


def _money(raw: Optional[str]) -> Optional[float]:
    """'₹31,999' -> 31999.0"""
    if not raw:
        return None
    m = re.search(r"[\d,]+(?:\.\d+)?", raw)
    return float(m.group(0).replace(",", "")) if m else None


def _first_float(raw: Optional[str]) -> Optional[float]:
    m = re.search(r"\d+(?:\.\d+)?", raw or "")
    return float(m.group(0)) if m else None


def _extract_json_ld(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract Schema.org Product data from json-ld scripts."""
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        return item
            elif isinstance(data, dict):
                if data.get("@type") == "Product":
                    return data
                if "@graph" in data:
                    for item in data["@graph"]:
                        if item.get("@type") == "Product":
                            return item
        except Exception:
            continue
    return {}


def detect_block(html: str, soup: BeautifulSoup):
    low = html[:200_000].lower()
    if "shieldsquare" in low or "enter the characters you see below" in low:
        raise BlockedOrChanged("Flipkart CAPTCHA / bot block detected")
    title = soup.select_one("h1, span.B_NuCI, h1._6EBuvT")
    if not title:
        raise BlockedOrChanged("Product title missing: possible block or unrecognized Flipkart layout")


def _upscale_flipkart_image(url: str) -> str:
    """Convert Flipkart thumbnail URL into maximum resolution (832x832 / 1664x1664)."""
    if not url:
        return url
    # e.g., .../image/128/128/... -> .../image/832/832/...
    return re.sub(r"/image/\d+/\d+/", "/image/832/832/", url)


def _extract_images(soup: BeautifulSoup, json_ld: Dict[str, Any]) -> List[str]:
    """Extract product images in high resolution."""
    images = []

    # From JSON-LD
    ld_img = json_ld.get("image")
    if isinstance(ld_img, str):
        images.append(_upscale_flipkart_image(ld_img))
    elif isinstance(ld_img, list):
        for u in ld_img:
            if isinstance(u, str):
                images.append(_upscale_flipkart_image(u))

    # From HTML gallery elements
    for img in soup.select("ul._3GnUWp img, div._2E1qri img, img.DByuf4, img._396cs4, img._2r_T1I"):
        src = img.get("src") or img.get("data-src")
        if src and "http" in src:
            hi_res = _upscale_flipkart_image(src)
            if hi_res not in images:
                images.append(hi_res)

    return images


def _extract_specifications(soup: BeautifulSoup) -> Dict[str, Dict[str, str]]:
    """Extract structured specs grouped by sections (General, Display, etc.)."""
    specs_by_group: Dict[str, Dict[str, str]] = {}
    current_group = "General"

    # Flipkart specs are grouped in tables or nested divs
    spec_sections = soup.select("div._3k-BhJ, div._1UhVsV, div.row._3q-0je")
    if spec_sections:
        for section in spec_sections:
            header_node = section.select_one("div.flx-header, div._2H87wv, div._3dGepu")
            if header_node:
                current_group = header_node.get_text(strip=True)
            if current_group not in specs_by_group:
                specs_by_group[current_group] = {}

            for row in section.select("tr._1s_Smc, tr.W_R1IA, tr"):
                k_node = row.select_one("td._1hKmbr, td:first-child")
                v_node = row.select_one("td._21lJal, td:last-child")
                if k_node and v_node and k_node != v_node:
                    k = k_node.get_text(strip=True)
                    v = v_node.get_text(" ", strip=True)
                    if k and v:
                        specs_by_group[current_group][k] = v
    else:
        # Fallback to any tables found inside specifications div
        for row in soup.select("table._14cfVK tr, table tr"):
            tds = row.select("td")
            if len(tds) >= 2:
                k = tds[0].get_text(strip=True)
                v = tds[1].get_text(" ", strip=True)
                if k and v:
                    if "General" not in specs_by_group:
                        specs_by_group["General"] = {}
                    specs_by_group["General"][k] = v

    return specs_by_group


def parse(html: str, source_url: Optional[str] = None) -> Dict[str, Any]:
    """Parse Flipkart product page HTML into structured dictionary."""
    soup = BeautifulSoup(html, "lxml")
    detect_block(html, soup)
    json_ld = _extract_json_ld(soup)

    # Canonical URL & Product ID
    canonical = (soup.select_one("link[rel=canonical]") or {}).get("href", "")
    target_urls = [source_url or "", canonical, (soup.select_one('meta[property="og:url"]') or {}).get("content", "")]
    product_id = None
    for u in target_urls:
        if u:
            fsn_m = FSN_RE.search(u)
            if fsn_m:
                product_id = fsn_m.group(1).upper()
                break

    if not product_id and "sku" in json_ld:
        product_id = str(json_ld["sku"]).strip()
    if not product_id:
        pid_node = soup.select_one('input[name="pid"], input[id="pid"]')
        if pid_node:
            product_id = pid_node.get("value")

    # Title
    title = (
        _text(soup, "h1._6EBuvT", "span.B_NuCI", "h1.yhB1nd", "h1") or
        json_ld.get("name")
    )

    # Price
    price = _money(_text(
        soup,
        "div.Nx9bqj.CxhGGd",
        "div._30jeq3._16J063",
        "div._30jeq3",
        "div._25bIlq",
    ))
    if price is None and "offers" in json_ld:
        offer = json_ld["offers"]
        if isinstance(offer, dict):
            price = _first_float(str(offer.get("price")))
        elif isinstance(offer, list) and offer:
            price = _first_float(str(offer[0].get("price")))

    # MRP (Original Price)
    mrp = _money(_text(
        soup,
        "div.yRaY8j.A68rqY",
        "div._3I9_wc._2p6lqe",
        "div._3I9_wc",
    ))
    if mrp is None:
        mrp = price

    # Rating & Reviews
    rating_val = (
        _first_float(_text(soup, "div.XQDdHH", "div._3LWZlK")) or
        _first_float(str(json_ld.get("aggregateRating", {}).get("ratingValue") if isinstance(json_ld.get("aggregateRating"), dict) else None))
    )

    # "12,345 Ratings & 1,234 Reviews"
    rating_review_text = _text(soup, "span.Wphh3N", "span._2_R_DZ")
    review_count = None
    if rating_review_text:
        rev_m = re.search(r"([\d,]+)\s*Reviews", rating_review_text, re.IGNORECASE)
        if rev_m:
            review_count = int(rev_m.group(1).replace(",", ""))
    if review_count is None and isinstance(json_ld.get("aggregateRating"), dict):
        review_count = int(json_ld["aggregateRating"].get("reviewCount") or 0) or None

    # Highlights
    bullets = [
        li.get_text(" ", strip=True)
        for li in soup.select("div._2c2kV- li, div._241VTa li, div._3XINqE li, div.x4t2NT li")
        if li.get_text(strip=True)
    ]

    # Images
    images = _extract_images(soup, json_ld)
    main_image = images[0] if images else None

    # Specifications grouped & flat
    grouped_specs = _extract_specifications(soup)
    flat_specs: Dict[str, str] = {}
    for g_items in grouped_specs.values():
        flat_specs.update(g_items)

    # Brand
    brand_line = json_ld.get("brand", {}).get("name") if isinstance(json_ld.get("brand"), dict) else None
    if not brand_line:
        brand_line = flat_specs.get("Model Name") or flat_specs.get("Brand")

    # Normalized tablet specs
    specs = normalize_tablet_specs(title or "", flat_specs)

    # Availability
    availability = "In Stock" if "out of stock" not in html.lower()[:100_000] else "Out of Stock"

    return {
        "platform": "flipkart",
        "product_id": product_id,
        "fsn": product_id,
        "url": canonical or source_url or None,
        "title": title,
        "brand_line": brand_line,
        "price_inr": price,
        "mrp_inr": mrp,
        "rating": rating_val,
        "review_count": review_count,
        "availability": availability,
        "bullets": bullets,
        "image": main_image,
        "images": images,
        "grouped_specs": grouped_specs,
        "tech_details": flat_specs,
        "specs": specs,
    }
