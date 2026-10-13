"""
main.py - Entrypoint for Tablet Scraper & WordPress Publisher.
Run directly to see options, or use cli.py for command-line arguments.
"""
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import cli

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # If no arguments provided, show help and status
        print("=" * 70)
        print("  📱 Tablet Scraper & WordPress/WooCommerce Publisher")
        print("=" * 70)
        print("\nQuick Commands:")
        print("  1. Parse saved HTML page(s):")
        print("     python cli.py parse <path_to_html_or_folder>")
        print("\n  2. View parsed listings & combined tablet comparison products:")
        print("     python cli.py list")
        print("\n  3. Test connection to your WordPress / WooCommerce site:")
        print("     python cli.py test-connection")
        print("\n  4. Publish combined tablet to WooCommerce:")
        print("     python cli.py post-wc --id <tablet_id>   (or --all)")
        print("\n  5. Standalone single-file parsers:")
        print("     python amazon_in_parser.py page.html")
        print("     python flipkart_in_parser.py page.html")
        print("=" * 70)
        print("\nShowing current database status:\n")
        cli.handle_list(None)
    else:
        cli.main()
