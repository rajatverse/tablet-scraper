"""
url_to_html_converter.py - Automatically fetch product page URL, save intact HTML, and parse details.

Supports:
- Amazon.in & Flipkart product URLs
- Single URL or multiple URLs via command line
- Batch URL processing from a text file (e.g. urls.txt)
- Interactive prompt if run without arguments
- Saves raw HTML to data/raw_html/
- Stores parsed results into SQLite database (data/tablets.db)
- Optionally exports parsed JSON files

Usage:
    python url_to_html_converter.py "https://www.amazon.in/dp/B0DK3Z6NMQ"
    python url_to_html_converter.py urls.txt
    python url_to_html_converter.py
"""
import sys
import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Enable UTF-8 encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config import RAW_HTML_DIR
from parsers import parse_page, detect_platform
from storage.db import Database

console = Console()
db = Database()

# Realistic desktop headers
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def extract_product_id(url: str, platform: str) -> str:
    """Extract ASIN for Amazon or PID/FSN for Flipkart."""
    if platform == "amazon":
        m = re.search(r"/(?:dp|product|gp/product)/([A-Z0-9]{10})", url, re.IGNORECASE)
        if m:
            return m.group(1).upper()
        m2 = re.search(r"\b([B0][A-Z0-9]{9})\b", url)
        if m2:
            return m2.group(1).upper()
    elif platform == "flipkart":
        m = re.search(r"[?&]pid=([A-Z0-9]{16})", url, re.IGNORECASE)
        if m:
            return m.group(1)
    
    # Fallback to sanitized slug
    slug = re.sub(r"[^\w\-]", "_", url.split("?")[0].rstrip("/").split("/")[-1])
    return slug[:24] or "product"


def fetch_and_save_html(url: str, output_dir: Path = RAW_HTML_DIR) -> Tuple[str, Path, str, str]:
    """
    Fetch URL using curl_cffi (browser TLS impersonation) or requests,
    and save pristine raw HTML to disk.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    html_content = ""
    fetch_url = url

    # Normalize Amazon shortlinks and URLs to clean /dp/{asin}
    try:
        import requests as std_requests
        # Check if Amazon shortlink or contains amazon
        if "link.amazon" in url or "amzn.to" in url or "amzn.in" in url or "amazon.in" in url:
            head_res = std_requests.get(url, allow_redirects=True, timeout=12)
            target = head_res.url
            asin_match = re.search(r"/(?:dp|product|gp/product)/([A-Z0-9]{10})", target, re.IGNORECASE)
            if asin_match:
                fetch_url = f"https://www.amazon.in/dp/{asin_match.group(1).upper()}"
            else:
                fetch_url = target
    except Exception:
        fetch_url = url

    final_url = fetch_url

    # Method 1: curl_cffi with Chrome impersonation (bypasses bot checks without clashing headers)
    try:
        from curl_cffi import requests as curl_requests
        resp = curl_requests.get(
            fetch_url,
            headers={"sec-ch-ua-mobile": "?0", "Accept-Language": "en-IN,en;q=0.9"},
            impersonate="chrome124",
            timeout=25,
            allow_redirects=True,
        )
        if resp.status_code == 200:
            html_content = resp.text
            final_url = str(resp.url) if resp.url else fetch_url
        else:
            console.print(f"[yellow]curl_cffi returned HTTP {resp.status_code}, trying requests fallback...[/yellow]")
    except Exception as e:
        console.print(f"[yellow]curl_cffi notice: {e}, falling back to requests...[/yellow]")

    # Method 2: Standard requests fallback
    if not html_content:
        import requests
        session = requests.Session()
        session.headers.update(BROWSER_HEADERS)
        resp = session.get(url, timeout=25, allow_redirects=True)
        if resp.status_code != 200:
            raise ConnectionError(f"HTTP {resp.status_code} returned when fetching {url}")
        html_content = resp.text
        final_url = str(resp.url) if resp.url else url

    if not html_content or len(html_content) < 1000:
        raise ValueError("Fetched page content is empty or too short (blocked by retailer).")

    # Detect platform & product ID from resolved destination URL
    platform = detect_platform(html_content, final_url)
    product_id = extract_product_id(final_url, platform)

    # In case product ID was not in URL, try parsing ASIN from HTML
    if platform == "amazon" and (product_id == "product" or len(product_id) != 10):
        asin_m = re.search(r'name=["\']ASIN["\']\s+value=["\']([A-Z0-9]{10})["\']', html_content)
        if asin_m:
            product_id = asin_m.group(1)

    html_filename = f"{platform}_{product_id}.html"
    target_path = output_dir / html_filename

    # Save raw HTML to file
    target_path.write_text(html_content, encoding="utf-8", errors="ignore")
    return html_content, target_path, platform, final_url


def check_already_added(url: str) -> Optional[Dict[str, Any]]:
    """Check if the product URL is already scraped and present in the database."""
    target_url = url
    if "link.amazon" in url or "amzn.to" in url or "amzn.in" in url:
        try:
            import requests as std_requests
            r = std_requests.get(url, allow_redirects=True, timeout=8)
            if r.url:
                target_url = r.url
        except Exception:
            pass

    platform = detect_platform("", target_url)
    product_id = extract_product_id(target_url, platform)
    if not product_id or product_id == "product":
        return None

    existing = db.get_listing_by_product_id(platform, product_id)
    if existing:
        tablet = db.get_tablet_by_listing_id(existing["id"])
        return {
            "listing": existing,
            "tablet": tablet,
            "platform": platform,
            "product_id": product_id,
        }
    return None



def convert_url(url: str, force: bool = False, save_json: bool = True, output_dir: Path = RAW_HTML_DIR) -> Optional[Dict[str, Any]]:
    """
    Complete pipeline with duplicate check:
    1. Check if product is already in database (skip download if exists unless force=True)
    2. Fetch live page URL
    3. Save raw HTML file to disk
    4. Parse HTML
    5. Store in SQLite database
    6. Optionally save JSON dump
    """
    url = url.strip()
    if not url or not url.startswith("http"):
        console.print(f"[red]Invalid URL:[/red] {url}")
        return None

    # Step 0: Check if product was already added
    if not force:
        check = check_already_added(url)
        if check:
            existing = check["listing"]
            tablet = check["tablet"]
            platform = check["platform"]
            product_id = check["product_id"]

            info_table = Table(show_header=False, box=None)
            info_table.add_column("Key", style="bold yellow")
            info_table.add_column("Value")
            info_table.add_row("Status", "[bold yellow]Already Exists in Database (Skipped)[/bold yellow]")
            info_table.add_row("Platform", platform.capitalize())
            info_table.add_row("Product ID", product_id)
            info_table.add_row("Title", str(existing.get("title") or "Unknown"))
            info_table.add_row("Price", f"₹{int(existing['price']):,}" if existing.get("price") else "N/A")
            info_table.add_row("Listing ID", f"#{existing['id']} (Updated: {existing.get('updated_at')})")
            
            if tablet:
                wc_status = tablet.get("wc_sync_status", "not_synced")
                wc_id = tablet.get("wc_product_id")
                status_color = "green" if wc_status == "synced" else "dim"
                info_table.add_row("WooCommerce", f"[{status_color}]{wc_status.capitalize()}[/{status_color}] (Product ID: #{wc_id or 'None'})")

            console.print(Panel(info_table, title="ℹ️ Product Already Added", border_style="yellow"))
            console.print("  [dim]Skipping download to avoid duplicate loading. (Use [bold cyan]--force[/bold cyan] to re-fetch and update).[/dim]\n")
            
            try:
                return json.loads(existing.get("data_json") or "{}")
            except Exception:
                return existing

    console.print(f"\n[cyan]🌐 Fetching URL:[/cyan] [link={url}]{url}[/link]")

    try:
        # Step 1 & 2: Fetch and save HTML
        html, html_path, platform, final_url = fetch_and_save_html(url, output_dir=output_dir)
        console.print(f"  [green]✓[/green] Saved raw HTML: [bold]{html_path.name}[/bold] ({len(html):,} bytes)")

        # Step 3: Parse saved HTML
        parsed = parse_page(html, platform=platform, source_url=final_url)
        
        # Step 4: Archive and save into SQLite
        db.save_raw_page(platform=platform, raw_html=html, product_id=parsed.get("product_id"), url=final_url, file_path=str(html_path))
        listing_id = db.save_listing(parsed)

        # Step 5: Save JSON file if requested
        if save_json:
            json_path = html_path.with_suffix(".json")
            json_path.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
            console.print(f"  [green]✓[/green] Saved parsed JSON: [bold]{json_path.name}[/bold]")

        # Display rich summary
        specs = parsed.get("specs") or {}
        price_str = f"₹{int(parsed['price_inr']):,}" if parsed.get("price_inr") else "N/A"
        mrp_str = f"₹{int(parsed['mrp_inr']):,}" if parsed.get("mrp_inr") else "N/A"
        rating_str = f"★ {parsed['rating']} ({parsed.get('review_count') or 0} reviews)" if parsed.get("rating") else "N/A"

        info_table = Table(show_header=False, box=None)
        info_table.add_column("Key", style="bold cyan")
        info_table.add_column("Value")
        info_table.add_row("Platform", platform.capitalize())
        info_table.add_row("Product ID", str(parsed.get("product_id")))
        info_table.add_row("Title", str(parsed.get("title")))
        info_table.add_row("Price / MRP", f"{price_str} (MRP: {mrp_str})")
        info_table.add_row("Rating", rating_str)
        info_table.add_row("Normalized Specs", f"{specs.get('brand')} | {specs.get('screen_size')} | {specs.get('storage')} | {specs.get('ram')} | {specs.get('connectivity')}")
        info_table.add_row("Database Listing", f"#{listing_id}")

        console.print(Panel(info_table, title=f"✓ Successfully Converted: {platform.capitalize()}", border_style="green"))
        return parsed

    except Exception as e:
        console.print(Panel(f"[bold red]Conversion Failed:[/bold red] {str(e)}", border_style="red"))
        return None


def main():
    parser = argparse.ArgumentParser(description="Convert Amazon & Flipkart Product URLs to Saved HTML and Parsed Data")
    parser.add_argument("source", nargs="?", help="Product URL or path to text file containing URLs")
    parser.add_argument("--force", "-f", action="store_true", help="Force re-fetch and update even if product already exists in database")
    parser.add_argument("--no-json", action="store_true", help="Do not save parsed .json file alongside .html")
    parser.add_argument("--output-dir", default=str(RAW_HTML_DIR), help="Directory to save raw HTML files")

    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    save_json = not args.no_json
    force = args.force

    urls = []
    if args.source:
        source_path = Path(args.source)
        if source_path.is_file():
            # Read URLs from file
            console.print(f"[cyan]Loading URLs from file:[/cyan] {source_path}")
            lines = source_path.read_text(encoding="utf-8").splitlines()
            urls = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
        else:
            urls = [args.source]
    else:
        # Interactive mode
        console.print("[bold yellow]No URL provided. Enter URL interactively:[/bold yellow]")
        try:
            user_input = input("Enter Amazon or Flipkart Product URL: ").strip()
            if user_input:
                urls = [user_input]
            else:
                console.print("[red]No URL entered. Exiting.[/red]")
                return
        except (KeyboardInterrupt, EOFError):
            return

    console.print(f"\n[bold]Starting conversion for {len(urls)} URL(s)...[/bold]")
    successful = 0
    for u in urls:
        res = convert_url(u, force=force, save_json=save_json, output_dir=output_dir)
        if res:
            successful += 1

    console.print(f"\n[bold green]✓ Conversion completed: {successful}/{len(urls)} processed.[/bold green]")
    console.print("View all parsed products with: [bold cyan]python cli.py list[/bold cyan]")


if __name__ == "__main__":
    main()

