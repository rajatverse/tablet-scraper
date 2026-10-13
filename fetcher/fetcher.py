"""
fetcher/fetcher.py - HTML loader and optional live fetcher.
Supports loading raw saved HTML files or fetching live URLs via curl_cffi/requests.
"""
from pathlib import Path
from typing import Optional, List, Tuple
import re

# Browser headers for fallback fetch
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def read_html_file(file_path: Path | str) -> str:
    """Read saved HTML page source from file."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"HTML file not found: {path}")

    # Try common encodings
    for enc in ("utf-8", "utf-8-sig", "latin1", "cp1252"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def list_html_files(folder_path: Path | str) -> List[Path]:
    """Scan directory for HTML files."""
    path = Path(folder_path)
    if not path.is_dir():
        return []
    return sorted(list(path.glob("*.html")) + list(path.glob("*.htm")))


def fetch_url(url: str, output_path: Optional[Path | str] = None) -> Tuple[str, Optional[Path]]:
    """
    Fetch live page HTML using curl_cffi (anti-bot bypass) or requests.
    Saves a copy if output_path is provided.
    """
    html_content = ""
    try:
        # Try curl_cffi first as it impersonates real browser TLS fingerprints
        from curl_cffi import requests as curl_requests
        resp = curl_requests.get(url, impersonate="chrome124", timeout=25, allow_redirects=True)
        html_content = resp.text
    except Exception:
        import requests
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=20)
        html_content = resp.text

    saved_file = None
    if output_path and html_content:
        saved_file = Path(output_path)
        saved_file.parent.mkdir(parents=True, exist_ok=True)
        saved_file.write_text(html_content, encoding="utf-8", errors="ignore")

    return html_content, saved_file
