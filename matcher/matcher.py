"""
matcher.py - Matches identical tablet models from Amazon and Flipkart into combined products.
"""
import re
from typing import Dict, Any, List, Optional
import urllib.parse
from config import AMAZON_AFFILIATE_TAG, FLIPKART_AFFILIATE_ID


def append_affiliate_tag(url: Optional[str], platform: str) -> Optional[str]:
    """Append affiliate parameters to the URL."""
    if not url:
        return None

    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)

    if platform == "amazon" and AMAZON_AFFILIATE_TAG:
        qs["tag"] = [AMAZON_AFFILIATE_TAG]
    elif platform == "flipkart" and FLIPKART_AFFILIATE_ID:
        qs["affid"] = [FLIPKART_AFFILIATE_ID]

    new_query = urllib.parse.urlencode(qs, doseq=True)
    return urllib.parse.urlunparse(parsed._replace(query=new_query))


def generate_match_key(product: Dict[str, Any]) -> str:
    """
    Generate a normalized match signature for a tablet product.
    Pattern: {brand}:{clean_model}:{storage}:{conn_simple}
    """
    specs = product.get("specs") or {}
    title = product.get("title") or ""

    brand = (specs.get("brand") or "").strip().lower()
    raw_model = (specs.get("model_name") or title).strip().lower()
    storage = (specs.get("storage") or "").strip().lower().replace(" ", "")
    conn = (specs.get("connectivity") or "").strip().lower()

    # Normalize connectivity
    if "5g" in conn or "4g" in conn or "cellular" in conn or "lte" in conn:
        conn_simple = "cellular"
    else:
        conn_simple = "wifi"

    # Normalize model string
    clean_model = re.sub(r"\b(?:generation)\b", "gen", raw_model, flags=re.IGNORECASE)
    clean_model = re.sub(r"[^\w\s]", "", clean_model)
    # Remove brand prefix if repeated
    if brand:
        clean_model = re.sub(rf"^{re.escape(brand)}\s*", "", clean_model, flags=re.IGNORECASE)
    clean_model = re.sub(r"\s+", "_", clean_model.strip())

    # Build key: brand:model:storage:connectivity
    parts = [brand, clean_model, storage, conn_simple]
    key = ":".join(p for p in parts if p)
    return key


def build_combined_tablet(
    amazon_item: Optional[Dict[str, Any]] = None,
    flipkart_item: Optional[Dict[str, Any]] = None,
    manual_title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Combine Amazon and Flipkart listings for the same tablet into a single record.
    """
    primary = amazon_item or flipkart_item
    if not primary:
        raise ValueError("At least one product listing (Amazon or Flipkart) is required.")

    specs = (amazon_item or {}).get("specs") or (flipkart_item or {}).get("specs") or {}

    # URLs & Affiliate links
    amz_raw_url = (amazon_item or {}).get("url")
    fk_raw_url = (flipkart_item or {}).get("url")
    amz_aff_url = append_affiliate_tag(amz_raw_url, "amazon")
    fk_aff_url = append_affiliate_tag(fk_raw_url, "flipkart")

    # Pricing
    amz_price = (amazon_item or {}).get("price_inr")
    fk_price = (flipkart_item or {}).get("price_inr")
    amz_mrp = (amazon_item or {}).get("mrp_inr")
    fk_mrp = (flipkart_item or {}).get("mrp_inr")

    prices = [p for p in [amz_price, fk_price] if p is not None]
    mrps = [m for m in [amz_mrp, fk_mrp] if m is not None]

    best_price = min(prices) if prices else None
    regular_price = max(mrps) if mrps else (best_price or 0.0)

    # Determine best store & primary external affiliate URL for WooCommerce
    if amz_price and fk_price:
        if amz_price <= fk_price:
            best_store = "Amazon"
            primary_aff_url = amz_aff_url
            primary_button_text = f"Buy on Amazon - ₹{int(amz_price):,}"
        else:
            best_store = "Flipkart"
            primary_aff_url = fk_aff_url
            primary_button_text = f"Buy on Flipkart - ₹{int(fk_price):,}"
    elif amz_price:
        best_store = "Amazon"
        primary_aff_url = amz_aff_url
        primary_button_text = f"Buy on Amazon - ₹{int(amz_price):,}"
    else:
        best_store = "Flipkart"
        primary_aff_url = fk_aff_url
        primary_button_text = f"Buy on Flipkart - ₹{int(fk_price):,}" if fk_price else "Check Price on Flipkart"

    # Merge images
    images = []
    if amazon_item and amazon_item.get("images"):
        images.extend(amazon_item["images"])
    if flipkart_item and flipkart_item.get("images"):
        for img in flipkart_item["images"]:
            if img not in images:
                images.append(img)
    main_image = images[0] if images else None

    # Merge bullets
    bullets = []
    if amazon_item and amazon_item.get("bullets"):
        bullets.extend(amazon_item["bullets"][:5])
    if flipkart_item and flipkart_item.get("bullets"):
        for b in flipkart_item["bullets"][:5]:
            if b not in bullets:
                bullets.append(b)

    # Clean display title
    brand = specs.get("brand") or "Tablet"
    model = specs.get("model_name") or primary.get("title", "")
    storage = specs.get("storage")
    screen = specs.get("screen_size")
    conn = specs.get("connectivity")
    color = specs.get("color")

    title_parts = [brand]
    if model and not model.lower().startswith(brand.lower()):
        title_parts.append(model)
    elif model:
        title_parts = [model]

    meta_parts = [p for p in [screen, storage, conn, color] if p]
    if meta_parts:
        display_title = f"{' '.join(title_parts)} ({', '.join(meta_parts)})"
    else:
        display_title = manual_title or primary.get("title") or "Tablet"

    # Full technical details merge
    full_specs = {}

    if amazon_item and amazon_item.get("overview"):
        full_specs.update(amazon_item["overview"])
    if flipkart_item and flipkart_item.get("tech_details"):
        full_specs.update(flipkart_item["tech_details"])
    if amazon_item and amazon_item.get("tech_details"):
        full_specs.update(amazon_item["tech_details"])

    # Verified normalized specs take precedence over retailer generic placeholders (e.g. iOS -> iPadOS 18)
    if specs:
        spec_mapping = [
            ("Brand", specs.get("brand")),
            ("Model Name", specs.get("model_name")),
            ("Screen Size", specs.get("screen_size")),
            ("Display Panel", specs.get("display_type")),
            ("Processor", specs.get("processor")),
            ("RAM", specs.get("ram")),
            ("Internal Storage", specs.get("storage")),
            ("Operating System", specs.get("operating_system")),
            ("Wireless Connectivity", specs.get("connectivity")),
            ("Battery Stamina", specs.get("battery")),
            ("Color", specs.get("color")),
        ]
        for k, v in spec_mapping:
            if v:
                full_specs[k] = str(v)

    return {
        "title": display_title,
        "brand": brand,
        "specs": specs,
        "full_specs": full_specs,
        "best_price": best_price,
        "regular_price": regular_price,
        "best_store": best_store,
        "primary_aff_url": primary_aff_url,
        "primary_button_text": primary_button_text,
        "amazon": {
            "asin": (amazon_item or {}).get("asin"),
            "price": amz_price,
            "mrp": amz_mrp,
            "rating": (amazon_item or {}).get("rating"),
            "review_count": (amazon_item or {}).get("review_count"),
            "url": amz_raw_url,
            "affiliate_url": amz_aff_url,
            "availability": (amazon_item or {}).get("availability"),
        } if amazon_item else None,
        "flipkart": {
            "fsn": (flipkart_item or {}).get("fsn"),
            "price": fk_price,
            "mrp": fk_mrp,
            "rating": (flipkart_item or {}).get("rating"),
            "review_count": (flipkart_item or {}).get("review_count"),
            "url": fk_raw_url,
            "affiliate_url": fk_aff_url,
            "availability": (flipkart_item or {}).get("availability"),
        } if flipkart_item else None,
        "main_image": main_image,
        "images": images,
        "bullets": bullets,
    }
