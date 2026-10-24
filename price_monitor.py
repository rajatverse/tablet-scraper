"""
price_monitor.py - Automated price checker and WooCommerce updater for TopTablets.

Features:
- Checks current pricing on Amazon.in and Flipkart.
- Only checks products where 3 days (configurable) have elapsed since the last check.
- If price is UNCHANGED: Updates last_price_checked timestamp and skips WooCommerce (zero redundant updates).
- If price CHANGED: Updates SQLite database, re-calculates savings, and automatically updates live WooCommerce product.
- Supports single run, continuous daemon loop, or Windows Task Scheduler automation.

Usage:
    python price_monitor.py                     # Check all listings due (>= 3 days old)
    python price_monitor.py --force             # Force check all listings now regardless of age
    python price_monitor.py --interval-days 1   # Check listings older than 1 day
    python price_monitor.py --daemon            # Run as a background service checking every 3 days
    python price_monitor.py --install-task      # Setup automated Windows Scheduled Task
"""
import sys
import os
import re
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

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

from config import RAW_HTML_DIR
from storage.db import Database
from parsers import parse_page, detect_platform
from wordpress.woocommerce_client import WooCommerceClient
from url_to_html_converter import fetch_and_save_html

console = Console()
db = Database()
wc = WooCommerceClient()


def check_single_listing_price(
    listing: Dict[str, Any],
    update_wc: bool = True
) -> Dict[str, Any]:
    """
    Fetch current live price for a single listing and compare with stored price.
    If changed: Updates SQLite and WooCommerce.
    If unchanged: Only updates last_price_checked timestamp.
    """
    listing_id = listing["id"]
    platform = listing["platform"]
    url = listing.get("url")
    old_price = listing.get("price")
    old_mrp = listing.get("mrp")
    title = listing.get("title") or f"Listing #{listing_id}"

    if not url:
        return {"status": "skipped", "reason": "No URL available", "listing_id": listing_id}

    console.print(f"\n[cyan]🔍 Checking Price:[/cyan] [bold]{title[:60]}[/bold]")
    console.print(f"  • Platform: [magenta]{platform.capitalize()}[/magenta] | Current DB Price: ₹{int(old_price):,}" if old_price else f"  • Platform: [magenta]{platform.capitalize()}[/magenta] | Current DB Price: N/A")

    try:
        # Fetch current live HTML
        html, html_path, detected_platform, final_url = fetch_and_save_html(url, output_dir=RAW_HTML_DIR)
        parsed = parse_page(html, platform=detected_platform, source_url=final_url)

        new_price = parsed.get("price_inr")
        new_mrp = parsed.get("mrp_inr")

        if new_price is None:
            # Price not found (could be out of stock, deal ended, or temporary captcha)
            console.print("  [yellow]⚠️ Price not detected on page (item may be Out of Stock or layout changed).[/yellow]")
            db.mark_listing_price_checked(listing_id)
            return {
                "status": "undetected",
                "listing_id": listing_id,
                "old_price": old_price,
                "new_price": None,
            }

        # Compare prices
        price_diff = (new_price - old_price) if (old_price is not None and new_price is not None) else None
        is_changed = (price_diff != 0) if price_diff is not None else (new_price != old_price)

        if not is_changed:
            # Price is identical - NO UPDATE NEEDED
            db.mark_listing_price_checked(listing_id)
            console.print(f"  [green]✓ Price Unchanged:[/green] ₹{int(new_price):,} [dim](No WooCommerce update needed)[/dim]")
            return {
                "status": "unchanged",
                "listing_id": listing_id,
                "price": new_price,
            }

        # Price HAS changed - Perform full update
        diff_str = f"+₹{int(price_diff):,}" if price_diff and price_diff > 0 else f"-₹{abs(int(price_diff)):,}" if price_diff else "New"
        console.print(f"  [bold yellow]⚡ Price Changed:[/bold yellow] ₹{int(old_price):,} → [bold green]₹{int(new_price):,}[/bold green] ({diff_str})")

        # 1. Update SQLite listing
        db.update_listing_price(listing_id, new_price, new_mrp)
        console.print("  [green]✓[/green] Updated database listing and re-calculated savings.")

        # 2. Update live WooCommerce product if synced
        wc_updated = False
        wc_product_id = None
        match_key = listing.get("match_key")
        if match_key and update_wc and wc.is_configured():
            tablet = db.get_tablet_by_match_key(match_key)
            if tablet and tablet.get("wc_product_id") and tablet.get("wc_sync_status") == "synced":
                wc_product_id = tablet["wc_product_id"]
                comb = json.loads(tablet["combined_json"])
                console.print(f"  [blue]Syncing updated pricing to WooCommerce product #{wc_product_id}...[/blue]")
                res = wc.publish_tablet(comb, existing_wc_id=wc_product_id)
                if res.get("success"):
                    wc_updated = True
                    console.print(f"  [bold green]✓ Live WooCommerce product #{wc_product_id} updated with new deal card & price![/bold green]")
                else:
                    console.print(f"  [red]✗ WooCommerce sync failed:[/red] {res.get('error')}")

        return {
            "status": "updated",
            "listing_id": listing_id,
            "old_price": old_price,
            "new_price": new_price,
            "wc_updated": wc_updated,
            "wc_product_id": wc_product_id,
        }

    except Exception as e:
        console.print(f"  [red]✗ Error checking price:[/red] {str(e)}")
        return {"status": "error", "error": str(e), "listing_id": listing_id}


def run_price_check(
    interval_days: float = 3.0,
    force: bool = False,
    update_wc: bool = True
) -> Dict[str, Any]:
    """
    Check all listings due for price inspection (>= interval_days since last check).
    """
    if force:
        listings = db.get_all_listings()
        console.print(f"\n[bold cyan]⚡ Running Forced Price Check on ALL {len(listings)} listings...[/bold cyan]")
    else:
        listings = db.get_listings_due_for_price_check(interval_days=interval_days)
        console.print(f"\n[bold cyan]📅 Checking Listings Due for Price Update (Interval: {interval_days} days)...[/bold cyan]")

    if not listings:
        console.print(Panel("[green]✓ All product prices are up-to-date![/green]\nNo listings are older than the 3-day interval window.", title="Price Monitor Status", border_style="green"))
        return {"total": 0, "updated": 0, "unchanged": 0, "errors": 0}

    console.print(f"Found [bold yellow]{len(listings)}[/bold yellow] listing(s) due for inspection.\n")

    summary = {"total": len(listings), "updated": 0, "unchanged": 0, "undetected": 0, "errors": 0}

    for idx, listing in enumerate(listings, 1):
        console.print(f"[dim]── [{idx}/{len(listings)}] ──────────────────────────────────────[/dim]")
        res = check_single_listing_price(listing, update_wc=update_wc)
        
        st = res.get("status")
        if st == "updated":
            summary["updated"] += 1
        elif st == "unchanged":
            summary["unchanged"] += 1
        elif st == "undetected":
            summary["undetected"] += 1
        else:
            summary["errors"] += 1

        # Polite rate-limiting sleep between live page fetches
        if idx < len(listings):
            time.sleep(2.0)

    # Summary Panel
    summary_table = Table(show_header=False, box=None)
    summary_table.add_column("Metric", style="bold")
    summary_table.add_column("Count")
    summary_table.add_row("Total Inspected", str(summary["total"]))
    summary_table.add_row("Prices Updated (WC Synced)", f"[bold green]{summary['updated']}[/bold green]")
    summary_table.add_row("Unchanged (No Update Needed)", f"[dim]{summary['unchanged']}[/dim]")
    summary_table.add_row("Errors / Blocked", f"[red]{summary['errors']}[/red]" if summary['errors'] else "0")

    console.print("\n")
    console.print(Panel(summary_table, title="🎯 Price Check Run Complete", border_style="cyan"))
    return summary


def run_daemon(interval_days: float = 3.0):
    """
    Run continuous background service checking every 3 days.
    """
    console.print(Panel(
        f"[bold green]TopTablets Auto Price Daemon Active[/bold green]\n"
        f"• Checking products older than: [bold]{interval_days} days[/bold]\n"
        f"• Continuous interval sleep: [bold]{interval_days} days[/bold]\n"
        f"Press [bold red]Ctrl + C[/bold red] to stop.",
        title="Daemon Started",
        border_style="green"
    ))

    sleep_seconds = int(interval_days * 24 * 3600)

    while True:
        try:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            console.print(f"\n[bold blue]⏰ [{now_str}] Starting scheduled price check cycle...[/bold blue]")
            run_price_check(interval_days=interval_days, force=False, update_wc=True)

            console.print(f"\n[dim]Next cycle in {interval_days} days ({sleep_seconds:,} seconds). Sleeping...[/dim]")
            time.sleep(sleep_seconds)
        except (KeyboardInterrupt, SystemExit):
            console.print("\n[yellow]Price monitor daemon stopped by user.[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Unexpected daemon error:[/red] {e}")
            console.print("[yellow]Retrying in 1 hour...[/yellow]")
            time.sleep(3600)


def generate_windows_task_command(interval_days: int = 3):
    """
    Generate PowerShell command to install a native Windows Scheduled Task.
    """
    python_exe = sys.executable
    script_path = Path(__file__).resolve()
    cwd = script_path.parent

    cmd = f'schtasks /create /tn "TopTablets-Price-Monitor" /tr "\\"{python_exe}\\" \\"{script_path}\\"" /sc daily /mo {interval_days} /st 04:00 /f'

    console.print(Panel(
        f"[bold cyan]Automate with Windows Task Scheduler (Runs in Background Every {interval_days} Days):[/bold cyan]\n\n"
        f"Run this command once in an Administrator PowerShell prompt:\n\n"
        f"[bold green]{cmd}[/bold green]\n\n"
        f"• Task Name: [bold]TopTablets-Price-Monitor[/bold]\n"
        f"• Frequency: Every [bold]{interval_days} days at 04:00 AM[/bold]\n"
        f"• Action: Checks prices & automatically updates WooCommerce only when prices change.",
        title="Windows Task Scheduler Setup",
        border_style="cyan"
    ))


def main():
    parser = argparse.ArgumentParser(description="TopTablets 3-Day Automated Price Checker & WooCommerce Updater")
    parser.add_argument("--interval-days", type=float, default=3.0, help="Check products older than N days (default: 3.0)")
    parser.add_argument("--force", "-f", action="store_true", help="Force check all products now regardless of last check date")
    parser.add_argument("--no-wc", action="store_true", help="Only update SQLite database, do not update WooCommerce")
    parser.add_argument("--daemon", "-d", action="store_true", help="Run continuously in background every N days")
    parser.add_argument("--install-task", action="store_true", help="Display Windows Scheduled Task command to run hands-free")

    args = parser.parse_args()

    if args.install_task:
        generate_windows_task_command(int(args.interval_days))
        return

    if args.daemon:
        run_daemon(interval_days=args.interval_days)
    else:
        run_price_check(interval_days=args.interval_days, force=args.force, update_wc=not args.no_wc)


if __name__ == "__main__":
    main()
