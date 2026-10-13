"""
amazon_parser.py - Robust parser for Amazon.in product pages.

Takes raw HTML string -> extracts structured product dictionary.
Incorporates tablet specification normalization.
"""
import json
import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from parsers.spec_normalizer import normalize_tablet_specs

ASIN_RE = re.compile(r"/dp/([A-Z0-9]{10})")


class BlockedOrChanged(Exception):
    """Raised when the HTML is a CAPTCHA/block page or the layout changed."""


def _text(soup: BeautifulSoup, *selectors: str) -> Optional[str]:
    """First non-empty text among fallback selectors."""
    for sel in selectors:
        for n in soup.select(sel):
            val = n.get_text(" ", strip=True)
            if val:
                return val
    return None


def _money(raw: Optional[str]) -> Optional[float]:
    """'₹69,900.00' -> 69900.0"""
    if not raw:
        return None
    m = re.search(r"[\d,]+(?:\.\d+)?", raw)
    return float(m.group(0).replace(",", "")) if m else None


def _first_float(raw: Optional[str]) -> Optional[float]:
    m = re.search(r"\d+(?:\.\d+)?", raw or "")
    return float(m.group(0)) if m else None


def _json_after(src: str, key: str) -> Optional[Any]:
    """Pull the JSON object that follows "key": {...} in inline scripts."""
    m = re.search(r'"%s"\s*:\s*(\{.*?\})\s*[,}]' % re.escape(key), src, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def detect_block(html: str, soup: BeautifulSoup):
    low = html[:200_000].lower()
    if "api-services-support@amazon" in low or "/errors/validatecaptcha" in low:
        raise BlockedOrChanged("Amazon CAPTCHA / bot-check page encountered")
    if not soup.select_one("#productTitle"):
        raise BlockedOrChanged("#productTitle missing: blocked page or layout change")


def _extract_images(soup: BeautifulSoup, html: str) -> List[str]:
    """Extract distinct high-resolution product image angles (front, back, profile, ports, in-hand)."""
    images = []
    seen_ids = set()

    def add_img(url: str):
        if not url:
            return
        m = re.search(r"/images/I/([A-Za-z0-9\+\%]+)\.", url)
        img_id = m.group(1) if m else url
        if img_id not in seen_ids:
            seen_ids.add(img_id)
            hi_res = re.sub(r"\._[A-Za-z0-9_,\-]+\.jpg", "._SL1500_.jpg", url)
            if not hi_res.endswith("._SL1500_.jpg") and ".jpg" in hi_res:
                hi_res = re.sub(r"\.jpg$", "._SL1500_.jpg", hi_res)
            images.append(hi_res)

    # 1. Main landing image
    landing = soup.select_one("#landingImage")
    if landing and landing.get("src"):
        add_img(landing["src"])

    # 2. Distinctive angles from altImages gallery
    for li in soup.select("#altImages ul li"):
        if "video" in str(li.get("class", [])).lower() or li.select_one(".a-icon-video, .video-icon"):
            continue
        img = li.select_one("img")
        if img and img.get("src"):
            src = img["src"]
            if "dp-play-icon" in src:
                continue
            add_img(src)

    # 3. ColorImages fallback
    color_matches = re.findall(r"'colorImages':\s*\{\s*'initial':\s*(\[.*?\])\s*\},", html, re.S)
    if color_matches:
        try:
            items = json.loads(color_matches[0])
            for it in items:
                hi = it.get("hiRes") or it.get("large")
                if hi:
                    add_img(hi)
        except Exception:
            pass

    return images[:5]


def parse(html: str, source_url: Optional[str] = None) -> Dict[str, Any]:
    """Parse Amazon.in HTML into structured product data."""
    soup = BeautifulSoup(html, "lxml")
    detect_block(html, soup)

    canonical = (soup.select_one("link[rel=canonical]") or {}).get("href", "")
    target_url = canonical or source_url or ""
    m = ASIN_RE.search(target_url)
    asin = m.group(1) if m else _text(soup, "#ASIN")
    if not asin:
        asin_input = soup.select_one('input[name="ASIN"]')
        if asin_input:
            asin = asin_input.get("value")

    # Price: visible buy-box price; MRP only exists when strike-through shows
    price = _money(_text(
        soup,
        "#corePriceDisplay_desktop_feature_div .priceToPay",
        "#corePrice_feature_div .a-price:not(.a-text-price) .a-offscreen",
        ".priceToPay",
        ".priceToPay .a-offscreen",
        "#apex_desktop .a-price:not(.a-text-price) .a-offscreen",
        "#corePriceDisplay_desktop_feature_div .a-price .a-offscreen",
        "#corePrice_feature_div .a-price .a-offscreen",
        ".a-price:not(.a-text-price) .a-offscreen",
        "#apex_desktop .a-price .a-offscreen",
        ".a-price .a-offscreen",
    ))
    mrp = _money(_text(
        soup,
        "#corePriceDisplay_desktop_feature_div .basisPrice .a-offscreen",
        "#corePrice_feature_div .basisPrice .a-offscreen",
        "#corePrice_feature_div .a-price.a-text-price .a-offscreen",
        "#corePriceDisplay_desktop_feature_div .a-text-price .a-offscreen",
        ".a-price.a-text-price .a-offscreen",
        ".basisPrice .a-offscreen",
        ".a-text-price .a-offscreen",
    ))

    rating_title = (soup.select_one("#acrPopover") or {}).get("title")
    reviews_raw = _text(soup, "#acrCustomerReviewText")

    images = _extract_images(soup, html)
    main_image = images[0] if images else None

    # Overview table (Brand, Model, Screen size, etc.)
    overview = {}
    for tr in soup.select("#productOverview_feature_div tr"):
        tds = tr.select("td")
        if len(tds) == 2:
            k = tds[0].get_text(strip=True)
            v = tds[1].get_text(strip=True)
            if k and v:
                overview[k] = v

    # Technical details table
    tech = {}
    for tr in soup.select("#productDetails_techSpec_section_1 tr, #productDetails_techSpec_section_2 tr, #technicalSpecifications_section_1 tr, #prodDetails tr"):
        th, td = tr.select_one("th"), tr.select_one("td")
        if th and td:
            k = th.get_text(strip=True).replace("\u200e", "").strip()
            v = td.get_text(strip=True).replace("\u200e", "").strip()
            if k and v:
                tech[k] = v

    # Bullets / Highlights
    bullets = [
        s.get_text(" ", strip=True)
        for s in soup.select("#feature-bullets li span")
        if s.get_text(strip=True) and "function(" not in s.get_text()
    ]

    title = _text(soup, "#productTitle")
    brand_line = _text(soup, "#bylineInfo")
    availability = _text(soup, "#availability span", "#availability")
    sold_by = _text(soup, "#merchantInfoFeature_feature_div")
    ships_from = _text(soup, "#fulfillerInfoFeature_feature_div")

    # Normalized tablet specs
    specs = normalize_tablet_specs(title or "", tech, overview)

    return {
        "platform": "amazon",
        "product_id": asin,
        "asin": asin,
        "url": canonical or source_url or (f"https://www.amazon.in/dp/{asin}" if asin else None),
        "title": title,
        "brand_line": brand_line,
        "price_inr": price,
        "mrp_inr": mrp or price,
        "rating": _first_float(rating_title),
        "review_count": int(re.sub(r"\D", "", reviews_raw)) if reviews_raw and re.search(r"\d", reviews_raw) else None,
        "availability": availability,
        "sold_by_text": sold_by,
        "ships_from_text": ships_from,
        "bullets": bullets,
        "image": main_image,
        "images": images,
        "overview": overview,
        "tech_details": tech,
        "specs": specs,
    }
