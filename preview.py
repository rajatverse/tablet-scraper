"""
preview.py - Export a standalone HTML preview of the WooCommerce product layout.
"""
from storage.db import Database
from wordpress.woocommerce_client import WooCommerceClient
import json

db = Database()
t = db.get_tablet_by_id(3)
comb = json.loads(t["combined_json"])
wc = WooCommerceClient()
payload = wc.build_payload(comb)

html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Preview: {payload['name']}</title>
</head>
<body style="background: #f8fafc; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <div style="max-width: 860px; margin: 0 auto; background: #ffffff; padding: 32px; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
    <h1 style="font-size: 1.6rem; color: #0f172a; margin-top: 0; font-weight: 800;">{payload['name']}</h1>
    <div style="margin-bottom: 24px;">{payload['short_description']}</div>
    <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0;">
    <div>{payload['description']}</div>
  </div>
</body>
</html>
"""

with open("data/preview_tablet.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("Preview written to data/preview_tablet.html")
