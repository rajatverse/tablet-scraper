"""
Unified parser interface for Amazon and Flipkart product pages.
"""
from typing import Dict, Any, Optional
from parsers import amazon_parser
from parsers import flipkart_parser


def detect_platform(html: str, source_url: Optional[str] = None) -> str:
    """Detect whether HTML belongs to Amazon or Flipkart."""
    low_url = (source_url or "").lower()
    if "amazon" in low_url or "amzn" in low_url:
        return "amazon"
    if "flipkart" in low_url or "fkrt" in low_url:
        return "flipkart"

    low_html = html[:20_000].lower()
    if "amazon" in low_html or "nav-logo-link" in low_html or "landingimage" in low_html:
        return "amazon"
    if "flipkart" in low_html or "flixcart" in low_html:
        return "flipkart"

    # Default fallback check
    if "id=\"productTitle\"" in html or "id='productTitle'" in html:
        return "amazon"

    return "amazon"  # default fallback


def parse_page(html: str, platform: Optional[str] = None, source_url: Optional[str] = None) -> Dict[str, Any]:
    """Parse HTML using the appropriate platform parser."""
    target_platform = (platform or "").lower()
    if not target_platform or target_platform == "auto":
        target_platform = detect_platform(html, source_url)

    if target_platform == "amazon":
        return amazon_parser.parse(html, source_url)
    elif target_platform == "flipkart":
        return flipkart_parser.parse(html, source_url)
    else:
        raise ValueError(f"Unsupported platform: {target_platform}. Supported: 'amazon', 'flipkart'")
