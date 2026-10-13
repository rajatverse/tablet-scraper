"""
flipkart_in_parser.py - parse a flipkart.com product page (HTML string -> dict).

Fetching is deliberately separate: save/fetch the HTML however you like,
store the raw copy, then run parse(). Re-parse stored HTML whenever a
selector needs fixing.

Usage:
    python flipkart_in_parser.py page.html
"""
import sys
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from parsers.flipkart_parser import parse

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python flipkart_in_parser.py <path_to_html_file>")
        sys.exit(1)

    html_file = sys.argv[1]
    with open(html_file, encoding="utf-8", errors="ignore") as f:
        html = f.read()

    result = parse(html)
    print(json.dumps(result, indent=2, ensure_ascii=False))
