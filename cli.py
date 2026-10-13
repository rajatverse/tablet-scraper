"""
cli.py - Rich Command Line Interface for Tablet Scraper & WordPress/WooCommerce Publisher.
"""
import sys
import os
import argparse
import json
from pathlib import Path

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from config import RAW_HTML_DIR, DB_PATH
from fetcher.fetcher import read_html_file, list_html_files, fetch_url
from parsers import parse_page, detect_platform
from storage.db import Database
from wordpress.woocommerce_client import WooCommerceClient

console = Console()
db = Database()


def handle_parse(args):
    """Parse one or more HTML files and store results."""
    target_path = Path(args.path)
    if not target_path.exists():
        console.print(f"[bold red]Error:[/bold red] Path does not exist: {target_path}")
        return

    files = list_html_files(target_path) if target_path.is_dir() else [target_path]
    if not files:
        console.print(f"[yellow]No HTML files found at {target_path}[/yellow]")
        return

    console.print(f"[bold cyan]Found {len(files)} file(s) to parse...[/bold cyan]")

    for f in files:
        console.print(f"\n[blue]Processing:[/blue] {f.name}")
        try:
            html = read_html_file(f)
            platform = args.platform if args.platform != "auto" else detect_platform(html)
            
            # Archive raw page in database
            db.save_raw_page(platform=platform, raw_html=html, file_path=str(f))

            # Parse
            parsed = parse_page(html, platform=platform)
            listing_id = db.save_listing(parsed)

            specs = parsed.get("specs") or {}
            console.print(f"  [green]✓[/green] Platform: [bold]{platform.capitalize()}[/bold]")
            console.print(f"  [green]✓[/green] Title: {parsed.get('title')}")
            console.print(f"  [green]✓[/green] Price: [bold]₹{parsed.get('price_inr') or 'N/A'}[/bold] (MRP: ₹{parsed.get('mrp_inr') or 'N/A'})")
            console.print(f"  [green]✓[/green] Specs: {specs.get('brand')} | {specs.get('screen_size')} | {specs.get('storage')} | {specs.get('connectivity')}")
            console.print(f"  [green]✓[/green] Stored listing ID: {listing_id}")

        except Exception as e:
            console.print(f"  [red]✗ Failed to parse {f.name}:[/red] {str(e)}")


def handle_fetch(args):
    """Fetch live page HTML and parse."""
    url = args.url
    platform = args.platform if args.platform != "auto" else detect_platform("", url)
    console.print(f"[cyan]Fetching live URL:[/cyan] {url}")
    
    timestamp = Path(url).stem or "page"
    save_file = RAW_HTML_DIR / f"{platform}_{timestamp[:20]}.html"

    try:
        html, saved_path = fetch_url(url, output_path=save_file)
        if not html:
            console.print("[red]Failed to retrieve HTML content.[/red]")
            return

        console.print(f"  [green]✓[/green] Saved raw HTML to: {saved_path}")
        parsed = parse_page(html, platform=platform, source_url=url)
        listing_id = db.save_listing(parsed)
        console.print(f"  [green]✓[/green] Successfully parsed and saved listing #{listing_id}")
    except Exception as e:
        console.print(f"[red]Error fetching/parsing:[/red] {str(e)}")


def handle_list(args):
    """Display stored listings and matched tablets in terminal tables."""
    listings = db.get_all_listings()
    tablets = db.get_all_tablets()

    console.print("\n[bold]📦 Stored Store Listings:[/bold]")
    if not listings:
        console.print("  [dim]No listings found. Parse some HTML files first.[/dim]")
    else:
        tbl = Table(title="Retail Listings (Amazon & Flipkart)", show_lines=True)
        tbl.add_column("ID", justify="right", style="cyan")
        tbl.add_column("Platform", style="magenta")
        tbl.add_column("Product ID", style="dim")
        tbl.add_column("Title", style="bold")
        tbl.add_column("Price (₹)", justify="right", style="green")
        tbl.add_column("Rating", justify="center")
        tbl.add_column("Match Key", style="yellow")

        for l in listings:
            price_str = f"₹{int(l['price']):,}" if l["price"] else "N/A"
            rating_str = f"★ {l['rating']}" if l["rating"] else "-"
            tbl.add_row(
                str(l["id"]),
                l["platform"].capitalize(),
                str(l["product_id"] or ""),
                l["title"][:55] + "..." if len(l["title"] or "") > 55 else str(l["title"] or ""),
                price_str,
                rating_str,
                str(l["match_key"] or ""),
            )
        console.print(tbl)

    console.print("\n[bold]📱 Combined Tablet Comparison Products:[/bold]")
    if not tablets:
        console.print("  [dim]No combined tablets available.[/dim]")
    else:
        tbl2 = Table(title="Combined Tablets (Ready for WooCommerce)", show_lines=True)
        tbl2.add_column("ID", justify="right", style="cyan")
        tbl2.add_column("Tablet Title", style="bold")
        tbl2.add_column("Amazon ₹", justify="right")
        tbl2.add_column("Flipkart ₹", justify="right")
        tbl2.add_column("Best Deal", style="bold green")
        tbl2.add_column("WC Status", style="magenta")
        tbl2.add_column("WC Post ID", justify="right")

        for t in tablets:
            comb = json.loads(t["combined_json"])
            amz = comb.get("amazon")
            fk = comb.get("flipkart")

            amz_p = f"₹{int(amz['price']):,}" if amz and amz.get("price") else "-"
            fk_p = f"₹{int(fk['price']):,}" if fk and fk.get("price") else "-"
            best = f"₹{int(t['best_price']):,} ({t['best_store']})" if t["best_price"] else "-"

            sync_style = "[green]Synced[/green]" if t["wc_sync_status"] == "synced" else "[dim]Draft[/dim]"
            tbl2.add_row(
                str(t["id"]),
                t["title"],
                amz_p,
                fk_p,
                best,
                sync_style,
                str(t["wc_product_id"] or "-"),
            )
        console.print(tbl2)


def handle_match(args):
    """Re-sync matches across all listings."""
    listings = db.get_all_listings()
    keys = set(l["match_key"] for l in listings if l["match_key"])
    console.print(f"[cyan]Re-indexing matches for {len(keys)} unique models...[/cyan]")
    for k in keys:
        db.sync_tablet_match(k)
    console.print("[green]Matching complete.[/green]")


def handle_test_connection(args):
    """Check WooCommerce REST API configuration."""
    wc = WooCommerceClient()
    console.print(f"[cyan]Testing connection to WordPress site:[/cyan] {wc.site_url}")
    res = wc.test_connection()
    if res["success"]:
        console.print(Panel(f"[bold green]Connection Successful![/bold green]\nSite: {res.get('site_title', 'WordPress')}\nWooCommerce Version: {res.get('wc_version', 'Detected')}", title="WooCommerce API Status"))
    else:
        console.print(Panel(f"[bold red]Connection Failed![/bold red]\n{res.get('error')}", title="WooCommerce API Error"))


def handle_post_wc(args):
    """Post combined tablet(s) to WooCommerce."""
    wc = WooCommerceClient()
    if not wc.is_configured():
        console.print("[red]WooCommerce is not configured! Please set credentials in .env[/red]")
        return

    tablets_to_post = []
    if args.id:
        t = db.get_tablet_by_id(args.id)
        if not t:
            console.print(f"[red]Tablet ID {args.id} not found.[/red]")
            return
        tablets_to_post.append(t)
    elif args.all:
        tablets_to_post = db.get_all_tablets()
    else:
        console.print("[yellow]Please specify --id <tablet_id> or --all to post.[/yellow]")
        return

    console.print(f"[bold cyan]Publishing {len(tablets_to_post)} tablet product(s) to WooCommerce...[/bold cyan]")

    for t in tablets_to_post:
        comb = json.loads(t["combined_json"])
        console.print(f"\n[blue]Publishing:[/blue] {t['title']}")
        console.print(f"  • Best Price: ₹{t.get('best_price')} on {t.get('best_store')}")

        res = wc.publish_tablet(comb, existing_wc_id=t.get("wc_product_id"))
        if res.get("success"):
            wc_id = res["wc_product_id"]
            db.update_wc_sync(t["id"], wc_id, status="synced")
            console.print(f"  [bold green]✓ Published successfully![/bold green]")
            console.print(f"  • Product ID: {wc_id}")
            if res.get("permalink"):
                console.print(f"  • URL: [link={res['permalink']}]{res['permalink']}[/link]")
        else:
            console.print(f"  [bold red]✗ Publish failed:[/bold red] {res.get('error')}")


def main():
    parser = argparse.ArgumentParser(
        description="Tablet Scraper & WordPress/WooCommerce Publisher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # parse
    p_parse = subparsers.add_parser("parse", help="Parse saved HTML file(s)")
    p_parse.add_argument("path", help="Path to .html file or directory containing HTML files")
    p_parse.add_argument("--platform", choices=["amazon", "flipkart", "auto"], default="auto", help="Retailer platform")
    p_parse.set_defaults(func=handle_parse)

    # fetch
    p_fetch = subparsers.add_parser("fetch", help="Fetch live URL and parse")
    p_fetch.add_argument("url", help="Product page URL")
    p_fetch.add_argument("--platform", choices=["amazon", "flipkart", "auto"], default="auto")
    p_fetch.set_defaults(func=handle_fetch)

    # list
    p_list = subparsers.add_parser("list", help="List parsed listings and combined tablets")
    p_list.set_defaults(func=handle_list)

    # match
    p_match = subparsers.add_parser("match", help="Re-sync model matching")
    p_match.set_defaults(func=handle_match)

    # test-connection
    p_test = subparsers.add_parser("test-connection", help="Test WordPress / WooCommerce REST API connection")
    p_test.set_defaults(func=handle_test_connection)

    # post-wc
    p_post = subparsers.add_parser("post-wc", help="Post combined tablet to WooCommerce")
    p_post.add_argument("--id", type=int, help="ID of the tablet to post")
    p_post.add_argument("--all", action="store_true", help="Post all tablets")
    p_post.set_defaults(func=handle_post_wc)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
