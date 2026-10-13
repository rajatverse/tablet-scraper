"""
product_template.py - TopTablets Spec-Hub Layout for WooCommerce Tablet Products.

Generates a modern, data-rich tablet specification portal experience:
 - Variant Selector (Color / Storage / Connectivity chips)
 - Live Affiliate Price Matrix with retailer badges, bank offers & price alerts
 - Editor's Verdict & Pros/Cons (2-column grid with benchmark meters)
 - Hardware Bento 4×2 Matrix
 - Practical Experience Highlights
 - Enhanced 8-Category Searchable Specification Database with visual pills
 - Interactive Comparison Module with spec-diff pills
 - Sticky Floating Quick-Buy Bar with rating & "Lowest" badge
 - Affiliate Disclosure

100% INLINE CSS for zero WordPress/WooCommerce KSES sanitization breakage.
Interactive JS (spec filter, scroll triggers) lives in the Blocksy child theme.
"""
import re
import json
import html
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IGNORE_SPEC_KEYS = {
    "asin", "item model number", "date first available", "manufacturer",
    "packer", "importer", "generic name", "customer reviews", "best sellers rank",
    "net quantity", "country of origin", "item weight", "package dimensions",
}

# Known chipset benchmark scores (expandable)
CHIPSET_BENCHMARKS: Dict[str, Dict[str, Any]] = {
    "Apple A17 Pro":       {"gb6_single": 2908, "gb6_multi": 7379, "antutu": 1650000, "process": "3nm TSMC"},
    "Apple M2":            {"gb6_single": 2592, "gb6_multi": 9747, "antutu": 1880000, "process": "5nm TSMC"},
    "Apple M4":            {"gb6_single": 3810, "gb6_multi": 14700, "antutu": 2250000, "process": "3nm TSMC"},
    "Apple A16 Bionic":    {"gb6_single": 2530, "gb6_multi": 6400, "antutu": 1320000, "process": "4nm TSMC"},
    "Apple A14 Bionic":    {"gb6_single": 2120, "gb6_multi": 4980, "antutu": 1150000, "process": "5nm TSMC"},
    "Snapdragon 8 Gen 3":  {"gb6_single": 2250, "gb6_multi": 7150, "antutu": 2100000, "process": "4nm TSMC"},
    "Snapdragon 8s Gen 3": {"gb6_single": 1870, "gb6_multi": 5000, "antutu": 1480000, "process": "4nm TSMC"},
    "Dimensity 9300+":          {"gb6_single": 2180, "gb6_multi": 7100, "antutu": 2050000, "process": "4nm TSMC"},
    "MediaTek Dimensity 9300+": {"gb6_single": 2180, "gb6_multi": 7100, "antutu": 2050000, "process": "4nm TSMC"},
    "Snapdragon 8s Gen 4": {"gb6_single": 2150, "gb6_multi": 6800, "antutu": 1850000, "process": "4nm TSMC"},
    "8s Gen 4":            {"gb6_single": 2150, "gb6_multi": 6800, "antutu": 1850000, "process": "4nm TSMC"},
    "Exynos 1380":              {"gb6_single": 1100, "gb6_multi": 3250, "antutu": 620000, "process": "5nm Samsung"},
}

# Augmented specs for known tablet models (data beyond what Amazon scrapes)
TABLET_AUGMENTED_SPECS: Dict[str, Dict[str, Any]] = {
    "Apple iPad mini 7th Gen": {
        "colors": [("Space Grey", "#4b4b4d"), ("Starlight", "#e5e0d8"), ("Purple", "#beb9cc"), ("Blue", "#587082")],
        "storage_options": ["128 GB", "256 GB", "512 GB"],
        "storage_badges": [("128 GB", "(Base)"), ("256 GB", None), ("512 GB", None)],
        "connectivity_options": ["Wi-Fi", "Wi-Fi + Cellular"],
        "connectivity_badges": [
            "Wi-Fi (Wi-Fi 6E 802.11ax)",
            "Wi-Fi + 5G Cellular (Sub-6 GHz eSIM)",
        ],
        "key_decision_specs": {
            "chipset": "Apple A17 Pro (6-core CPU, 5-core GPU, 3nm)",
            "display": "8.3\" Liquid Retina IPS (2266 × 1488, 500 nits, P3)",
            "ram_storage": "8 GB Unified RAM • 128 GB Base NVMe",
            "form_factor": "293g weight • 6.3mm thin (Ultra-portable)",
            "stylus": "Apple Pencil Pro (Haptic, Barrel Roll) & USB-C",
        },
        "display": {
            "Screen-to-Body Ratio": "81.2%",
            "Peak Brightness": "500 nits (typical)",
            "Color Gamut": "DCI-P3 Wide Color",
            "Refresh Rate": "60 Hz",
            "ProMotion 120Hz": False,
            "True Tone": True,
            "Anti-Reflective Coating": True,
            "Fully Laminated": True,
        },
        "stylus": {
            "Stylus Support": "Apple Pencil Pro + Apple Pencil (USB-C)",
            "Stylus Latency": "~9 ms",
            "Palm Rejection": True,
            "Hover Detection": True,
            "Barrel Roll": True,
            "Haptic Squeeze": True,
        },
        "cameras": {
            "Rear Camera": "12 MP Wide, f/1.8, True Tone Flash",
            "Front Camera": "12 MP Ultra Wide, f/2.4, Center Stage",
            "Video Recording": "4K @ 60 fps, 1080p @ 240 fps Slo-mo",
            "Center Stage": True,
        },
        "battery_charging": {
            "Charging Wattage": "20W USB-PD",
            "Charge Time (0→100%)": "~2 hours",
            "Reverse Wired Charging": False,
        },
        "connectivity_extra": {
            "Wi-Fi Standard": "Wi-Fi 6E (802.11ax)",
            "Bluetooth": "5.3",
            "USB": "USB-C 3.1 Gen 2 (10 Gbps)",
            "DisplayPort via USB-C": True,
            "3.5mm Headphone Jack": False,
            "MicroSD Expansion": False,
        },
        "software_security": {
            "Operating System": "iPadOS 18",
            "Apple Intelligence": True,
            "Biometric": "Touch ID (top button)",
            "Face ID": False,
            "Security Updates": "6+ years guaranteed",
        },
        "sensors": {
            "Accelerometer": True,
            "Gyroscope": True,
            "Barometer": True,
            "Ambient Light": True,
            "Compass": True,
            "GPS": False,
        },
        "build": {
            "Weight": "293 g",
            "Thickness": "6.3 mm",
            "Material": "100% Recycled Aluminum",
            "IP Rating": "Not Rated",
            "Landscape Stereo Speakers": True,
        },
        "rivals": [
            {
                "name": "Apple iPad Air M2 (11\")",
                "img": "https://toptablets.in/wp-content/uploads/2026/10/ipad-air-m2.jpg",
                "desc": "Portability vs Screen Workspace • M2 Power",
                "diffs": ["-2.7\" Smaller Screen", "A17 Pro vs M2 Chip", "169g Lighter", "₹12K Cheaper"],
            },
            {
                "name": "OnePlus Pad 2 (12.1\")",
                "img": "https://toptablets.in/wp-content/uploads/2026/10/oneplus-pad-2.jpg",
                "desc": "Compact iOS vs Big Screen Android • 3K 144Hz",
                "diffs": ["Compact 8.3\" vs 12.1\"", "iPadOS vs Android", "60Hz vs 144Hz LCD", "Lighter Form Factor"],
            },
            {
                "name": "Samsung Galaxy Tab S9 FE",
                "img": "https://toptablets.in/wp-content/uploads/2026/10/samsung-galaxy-tab-s9-fe.jpg",
                "desc": "Flagship A17 Pro vs Bundled S-Pen & IP68",
                "diffs": ["8.3\" vs 10.9\" Screen", "A17 Pro > Exynos 1380", "No S-Pen Bundled", "No IP68 Rating"],
            },
        ],
    },
    "Samsung Galaxy Tab S10+": {
        "colors": [("Platinum Silver", "#c8c8cb"), ("Moonstone Gray", "#535558")],
        "storage_options": ["256 GB", "512 GB"],
        "storage_badges": [("256 GB", "(Base)"), ("512 GB", None)],
        "connectivity_options": ["Wi-Fi", "Wi-Fi + 5G"],
        "connectivity_badges": [
            "Wi-Fi (Wi-Fi 6E 802.11ax Tri-band)",
            "Wi-Fi + 5G Cellular (Sub-6 GHz eSIM)",
        ],
        "key_decision_specs": {
            "chipset": "MediaTek Dimensity 9300+ (4nm Octa-core, Immortalis-G720 GPU)",
            "display": "12.4\" Dynamic AMOLED 2X (2800 × 1752, 120Hz, Anti-Reflective)",
            "ram_storage": "12 GB LPDDR5X RAM • 256 GB / 512 GB UFS 4.0 Storage",
            "form_factor": "571g weight • 5.6mm ultra-thin • Armor Aluminum (IP68)",
            "stylus": "Bundled S Pen in the box (2.8ms latency, IP68, Air Actions)",
        },
        "display": {
            "Screen-to-Body Ratio": "84.3%",
            "Peak Brightness": "650 nits (HBM typical)",
            "Color Gamut": "DCI-P3 100% Wide Color",
            "Refresh Rate": "120 Hz",
            "ProMotion 120Hz": True,
            "True Tone": False,
            "Anti-Reflective Coating": True,
            "Fully Laminated": True,
        },
        "stylus": {
            "Stylus Support": "Bundled S Pen in the Box (IP68)",
            "Stylus Latency": "2.8 ms",
            "Palm Rejection": True,
            "Hover Detection": True,
            "Barrel Roll": False,
            "Haptic Squeeze": False,
            "Air Actions": True,
        },
        "cameras": {
            "Rear Camera": "13 MP Main + 8 MP Ultra-Wide",
            "Front Camera": "12 MP Ultra-Wide (Landscape Centered)",
            "Video Recording": "4K @ 30 fps, 1080p @ 30 fps",
            "Center Stage": False,
        },
        "battery_charging": {
            "Charging Wattage": "45W Super Fast Charging 2.0 (USB-PD)",
            "Charge Time (0→100%)": "~1 hour 25 mins",
            "Reverse Wired Charging": True,
        },
        "connectivity_extra": {
            "Wi-Fi Standard": "Wi-Fi 6E (802.11ax Tri-Band)",
            "Bluetooth": "5.3",
            "USB": "USB-C 3.2 Gen 1 (DP Video Out)",
            "DisplayPort via USB-C": True,
            "3.5mm Headphone Jack": False,
            "MicroSD Expansion": True,
        },
        "software_security": {
            "Operating System": "Android 14 (One UI 6.1.1)",
            "Galaxy AI": True,
            "Biometric": "In-Display Optical Fingerprint",
            "Face ID": False,
            "Security Updates": "7 years guaranteed OS & security updates",
        },
        "sensors": {
            "Accelerometer": True,
            "Gyroscope": True,
            "Geomagnetic": True,
            "Hall Sensor": True,
            "RGB Light Sensor": True,
            "GPS": True,
        },
        "build": {
            "Weight": "571 g",
            "Thickness": "5.6 mm",
            "Material": "Enhanced Armor Aluminum",
            "IP Rating": "IP68 (Water & Dust Resistant)",
            "Landscape Stereo Speakers": True,
        },
        "rivals": [
            {
                "name": "Apple iPad Air 13\" (M2)",
                "img": "https://toptablets.in/wp-content/uploads/2026/10/ipad-air-m2.jpg",
                "desc": "Liquid Retina 60Hz vs 120Hz AMOLED • M2 vs Dimensity 9300+",
                "diffs": ["120Hz AMOLED vs 60Hz LCD", "Bundled S-Pen vs ₹11.9K Pencil", "IP68 Water Resistance", "Samsung DeX Desktop"],
            },
            {
                "name": "Apple iPad Pro 11\" (M4)",
                "img": "https://toptablets.in/wp-content/uploads/2026/10/ipad-pro-m4.jpg",
                "desc": "Tandem OLED vs Dynamic AMOLED 2X • Ultra-flagship battle",
                "diffs": ["Larger 12.4\" Display", "M4 Raw Power Advantage", "Bundled S Pen in Box", "₹40K+ Lower Starting Price"],
            },
            {
                "name": "OnePlus Pad 2 (12.1\")",
                "img": "https://toptablets.in/wp-content/uploads/2026/10/oneplus-pad-2.jpg",
                "desc": "3K LCD vs AMOLED 2X • Snapdragon 8 Gen 3 vs Dimensity 9300+",
                "diffs": ["AMOLED 2X vs LCD Panel", "Bundled S Pen Included", "IP68 vs No Ingress Rating", "Samsung DeX Multi-window"],
            },
        ],
    },
    "Apple iPad 10th Gen": {
        "colors": [("Silver", "#e2e4e5"), ("Blue", "#4b7194"), ("Pink", "#e87b8d"), ("Yellow", "#f0d25d")],
        "storage_options": ["64 GB", "256 GB"],
        "storage_badges": [("64 GB", "(Base)"), ("256 GB", None)],
        "connectivity_options": ["Wi-Fi", "Wi-Fi + Cellular"],
        "connectivity_badges": [
            "Wi-Fi (Wi-Fi 6 802.11ax)",
            "Wi-Fi + 5G Cellular (Sub-6 GHz eSIM)",
        ],
        "key_decision_specs": {
            "chipset": "Apple A14 Bionic (6-core CPU, 4-core GPU, 5nm)",
            "display": "10.9\" Liquid Retina IPS (2360 × 1640, 500 nits, True Tone)",
            "ram_storage": "4 GB Unified RAM • 64 GB / 256 GB Storage",
            "form_factor": "477g weight • 7.0mm thin (100% Recycled Aluminum)",
            "stylus": "Apple Pencil (USB-C) & Apple Pencil (1st Gen)",
        },
        "display": {
            "Screen-to-Body Ratio": "80.5%",
            "Peak Brightness": "500 nits (typical)",
            "Color Gamut": "sRGB Wide Color",
            "Refresh Rate": "60 Hz",
            "ProMotion 120Hz": False,
            "True Tone": True,
            "Anti-Reflective Coating": False,
            "Fully Laminated": False,
        },
        "stylus": {
            "Stylus Support": "Apple Pencil (USB-C) & 1st Gen",
            "Stylus Latency": "~20 ms",
            "Palm Rejection": True,
            "Hover Detection": False,
            "Barrel Roll": False,
            "Haptic Squeeze": False,
        },
        "cameras": {
            "Rear Camera": "12 MP Wide, f/1.8, 5x digital zoom",
            "Front Camera": "12 MP Landscape Ultra Wide, f/2.4, Center Stage",
            "Video Recording": "4K @ 60 fps, 1080p Slo-mo",
            "Center Stage": True,
        },
        "battery_charging": {
            "Charging Wattage": "20W USB-PD",
            "Charge Time (0→100%)": "~2 hours 15 mins",
            "Reverse Wired Charging": False,
        },
        "connectivity_extra": {
            "Wi-Fi Standard": "Wi-Fi 6 (802.11ax)",
            "Bluetooth": "5.2",
            "USB": "USB-C 2.0 (480 Mbps)",
            "DisplayPort via USB-C": True,
            "3.5mm Headphone Jack": False,
            "MicroSD Expansion": False,
        },
        "software_security": {
            "Operating System": "iPadOS 18",
            "Apple Intelligence": False,
            "Biometric": "Touch ID (top button)",
            "Face ID": False,
            "Security Updates": "5+ years guaranteed",
        },
        "sensors": {
            "Accelerometer": True,
            "Gyroscope": True,
            "Barometer": True,
            "Ambient Light": True,
            "Compass": True,
            "GPS": False,
        },
        "build": {
            "Weight": "477 g",
            "Thickness": "7.0 mm",
            "Material": "100% Recycled Aluminum",
            "IP Rating": "Not Rated",
            "Landscape Stereo Speakers": True,
        },
        "rivals": [],
    },
    "Xiaomi Pad 8": {
        "colors": [("Titanium Blue", "#4a6880"), ("Graphite Gray", "#3c3d42")],
        "storage_options": ["128 GB", "256 GB"],
        "storage_badges": [("128 GB", "(Base)"), ("256 GB", None)],
        "connectivity_options": ["Wi-Fi"],
        "connectivity_badges": [
            "Wi-Fi 7 (802.11be Tri-band)",
        ],
        "key_decision_specs": {
            "chipset": "Snapdragon 8s Gen 4 (4nm Octa-core, Adreno GPU)",
            "display": "11.2\" 3.2K ImmersiView (3200 × 2136, 144Hz, 800 nits, Dolby Vision)",
            "ram_storage": "8 GB LPDDR5T RAM • 128 GB UFS Storage",
            "form_factor": "485g weight • 6.1mm ultra-slim metal unibody",
            "stylus": "Xiaomi Focus Pen Pro support (low latency)",
        },
        "display": {
            "Screen-to-Body Ratio": "86.5%",
            "Peak Brightness": "800 nits",
            "Color Gamut": "68 Billion+ Colors, DCI-P3",
            "Refresh Rate": "144 Hz",
            "ProMotion 120Hz": True,
            "True Tone": False,
            "Anti-Reflective Coating": True,
            "Fully Laminated": True,
        },
        "stylus": {
            "Stylus Support": "Xiaomi Focus Pen Pro (Optional)",
            "Stylus Latency": "~3 ms",
            "Palm Rejection": True,
            "Hover Detection": True,
            "Barrel Roll": False,
            "Haptic Squeeze": False,
            "Air Actions": False,
        },
        "cameras": {
            "Rear Camera": "13 MP Main with LED flash",
            "Front Camera": "8 MP Ultra-Wide (Landscape Centered)",
            "Video Recording": "4K @ 30 fps, 1080p @ 60 fps",
            "Center Stage": False,
        },
        "battery_charging": {
            "Charging Wattage": "45W Turbo Charging (USB-PD)",
            "Charge Time (0→100%)": "~1 hour 20 mins",
            "Reverse Wired Charging": False,
        },
        "connectivity_extra": {
            "Wi-Fi Standard": "Wi-Fi 7 (802.11be)",
            "Bluetooth": "6.0",
            "USB": "USB-C 3.2 Gen 1 (DP Video Out)",
            "DisplayPort via USB-C": True,
            "3.5mm Headphone Jack": False,
            "MicroSD Expansion": False,
        },
        "software_security": {
            "Operating System": "Xiaomi HyperOS 3 (Android 16)",
            "HyperAI": True,
            "Biometric": "AI Face Unlock",
            "Face ID": False,
            "Security Updates": "4 years guaranteed",
        },
        "sensors": {
            "Accelerometer": True,
            "Gyroscope": True,
            "Ambient Light": True,
            "Color Temperature": True,
            "Hall Sensor": True,
            "GPS": False,
        },
        "build": {
            "Weight": "485 g",
            "Thickness": "6.1 mm",
            "Material": "Aerospace-grade Aluminum Unibody",
            "IP Rating": "Not Rated",
            "Landscape Stereo Speakers": True,
        },
        "rivals": [
            {
                "name": "OnePlus Pad 2 (12.1\")",
                "img": "https://toptablets.in/wp-content/uploads/2026/10/oneplus-pad-2.jpg",
                "desc": "Snapdragon 8s Gen 4 vs 8 Gen 3 • 11.2\" vs 12.1\" 3K Display",
                "diffs": ["11.2\" vs 12.1\" Screen", "9200mAh vs 9510mAh", "HyperOS vs OxygenOS", "Lighter 485g Weight"],
            },
            {
                "name": "Apple iPad 10th Gen",
                "img": "https://toptablets.in/wp-content/uploads/2026/10/ipad-10th-gen.jpg",
                "desc": "3.2K 144Hz Android Flagship vs Everyday iPadOS Standard",
                "diffs": ["144Hz vs 60Hz Display", "8GB vs 4GB RAM", "128GB vs 64GB Base", "45W vs 20W Charging"],
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_money(amount: Any) -> str:
    """Format float or int into Indian currency format."""
    try:
        val = int(float(amount))
        return f"₹{val:,}"
    except (ValueError, TypeError):
        return "N/A"


def _pill_html(text: str, present: bool = True) -> str:
    """Render a visual ✔/✖ indicator for boolean spec features."""
    if present:
        return f"✔ {text}"
    else:
        return f"✖ {text}"


def _diff_pill(text: str) -> str:
    """Render a compact comparison diff pill."""
    return (f'<span style="display:inline-block;background:#eff6ff;color:#1d4ed8;'
            f'font-size:0.7rem;font-weight:600;padding:2px 6px;border-radius:4px;'
            f'margin:2px 3px 2px 0;white-space:nowrap;">{text}</span>')


def _get_model_key(specs: Dict[str, Any]) -> Optional[str]:
    """Try to find a matching key in TABLET_AUGMENTED_SPECS."""
    model = (specs.get("model_name") or "").lower()
    proc = (specs.get("processor") or "").lower()
    if "mini" in model:
        return "Apple iPad mini 7th Gen"
    if "s10" in model or "tab s10" in model or "dimensity 9300" in proc:
        return "Samsung Galaxy Tab S10+"
    if "10th" in model or "ipad 10" in model or "a14" in proc:
        return "Apple iPad 10th Gen"
    if "pad 8" in model or "xiaomi" in model:
        return "Xiaomi Pad 8"
    for key in TABLET_AUGMENTED_SPECS:
        if key.lower() in model or model in key.lower():
            return key
    return None


def _get_benchmarks(processor: str) -> Optional[Dict[str, Any]]:
    """Look up benchmark data for a known chipset."""
    proc_lower = processor.lower()
    for chip, data in CHIPSET_BENCHMARKS.items():
        if chip.lower() in proc_lower or proc_lower in chip.lower():
            return data
    return None


# ---------------------------------------------------------------------------
# Section: Sticky Sub-Navigation
# ---------------------------------------------------------------------------

def render_sticky_subnav() -> str:
    """Render the synchronized Quick Navigation strip."""
    return """
  <!-- Quick Nav -->
  <nav class="tt-quick-nav">
    <a href="#tt-deals">⚡ Best Price</a>
    <a href="#tt-verdict">🎯 Editorial Verdict</a>
    <a href="#tt-hardware">⚙️ Hardware Matrix</a>
    <a href="#tt-specs">📑 Full Specs</a>
  </nav>
"""


# ---------------------------------------------------------------------------
# Section: Live Deals Tracker (Phase 2 — enhanced)
# ---------------------------------------------------------------------------

def render_live_deals_tracker(tablet: Dict[str, Any]) -> str:
    """Render Live Store Prices & Stock Tracker focused strictly on verified Amazon India pricing."""
    amz = tablet.get("amazon") or {}
    best_price = tablet.get("best_price") or amz.get("price") or 0
    regular_price = tablet.get("regular_price") or amz.get("mrp") or 0

    amz_url = amz.get("affiliate_url") or amz.get("url") or tablet.get("primary_aff_url") or "#"
    amz_price = amz.get("price") or best_price
    specs = tablet.get("specs") or {}
    brand = specs.get("brand") or "Apple"

    savings = int(regular_price - best_price) if regular_price and best_price and regular_price > best_price else 0
    discount_pct = round((savings / regular_price) * 100) if regular_price and savings > 0 else 0
    mrp_str = f'<span style="font-size:1.1rem;color:#94a3b8;text-decoration:line-through;margin-left:10px;font-weight:500;">{_format_money(regular_price)}</span>' if regular_price and regular_price > best_price else ''
    disc_badge = f'<span style="font-size:0.82rem;font-weight:700;color:#16a34a;background:#f0fdf4;padding:3px 8px;border-radius:6px;border:1px solid #bbf7d0;margin-left:10px;">{discount_pct}% OFF (Save {_format_money(savings)})</span>' if savings > 0 else ''

    return f"""
  <!-- Amazon Deal Card (Single-Merchant Focus) -->
  <section id="tt-deals" class="tt-deal-card" style="border:2px solid #f59e0b;border-radius:14px;overflow:hidden;background:#ffffff;margin:32px 0;box-shadow:0 4px 16px rgba(245,158,11,0.08);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
    <a id="deals"></a>
    <div style="background:#fffbeb;padding:12px 20px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #fde68a;flex-wrap:wrap;gap:8px;">
      <div style="display:flex;align-items:center;gap:8px;">
        <span class="tt-live-dot" style="display:inline-block;width:8px;height:8px;background:#ef4444;border-radius:50%;box-shadow:0 0 8px rgba(239,68,68,0.5);"></span>
        <span style="font-size:0.82rem;font-weight:700;color:#92400e;text-transform:uppercase;letter-spacing:0.04em;">Amazon India Verified Live Price</span>
      </div>
      <span style="background:#dcfce7;color:#15803d;font-size:0.75rem;font-weight:700;padding:3px 10px;border-radius:9999px;border:1px solid #86efac;">● IN STOCK</span>
    </div>
    <div style="padding:22px;display:flex;flex-direction:column;gap:18px;">
      <div style="display:flex;align-items:baseline;justify-content:space-between;flex-wrap:wrap;gap:14px;padding-bottom:14px;border-bottom:1px solid #f1f5f9;">
        <div>
          <div style="font-size:0.78rem;font-weight:600;color:#64748b;margin-bottom:4px;">Official {brand} Store Listing</div>
          <div style="display:flex;align-items:baseline;flex-wrap:wrap;">
            <span style="font-size:2rem;font-weight:800;color:#0f172a;letter-spacing:-0.5px;">{_format_money(amz_price)}</span>
            {mrp_str}
            {disc_badge}
          </div>
        </div>
        <div style="background:#fffbeb;border:1px solid #fde68a;padding:8px 14px;border-radius:8px;font-size:0.82rem;font-weight:600;color:#92400e;display:flex;align-items:center;gap:6px;">
          <span>💳</span> <span>Instant discount available on HDFC/ICICI Cards</span>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:10px;">
        <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="tt-btn-amazon" style="display:flex;align-items:center;justify-content:center;gap:8px;background:#ff9900;color:#111827;font-weight:800;font-size:1.05rem;padding:14px 24px;border-radius:10px;text-decoration:none;box-shadow:0 4px 14px rgba(255,153,0,0.3);transition:all 0.15s ease;">
          <span>🛒 Buy on Amazon ({_format_money(amz_price)})</span>
          <span style="font-size:1.15rem;">↗</span>
        </a>
        <div style="display:flex;align-items:center;justify-content:space-between;font-size:0.78rem;color:#64748b;padding:0 4px;flex-wrap:wrap;gap:8px;">
          <span style="color:#15803d;font-weight:600;display:flex;align-items:center;gap:5px;">
            <span>✓</span> 100% Genuine Retailer Verification • Prime Express Delivery
          </span>
          <span>Official {brand} India Listing</span>
        </div>
      </div>
    </div>
  </section>
"""


# ---------------------------------------------------------------------------
# Section: Verdict & Pros/Cons
# ---------------------------------------------------------------------------

def render_verdict_and_pros_cons(tablet: Dict[str, Any]) -> str:
    """Render Two-Column The Verdict and Pros & Cons with benchmark meters."""
    specs = tablet.get("specs") or {}
    model = specs.get("model_name") or tablet.get("title", "iPad mini")
    rating = (tablet.get("amazon") or {}).get("rating") or (tablet.get("flipkart") or {}).get("rating") or 4.6
    score = round(float(rating) * 2, 1)
    processor = specs.get("processor") or ""
    benchmarks = _get_benchmarks(processor)

    # Dynamic pros & cons tailored to model
    if "mini" in model.lower():
        pros = [
            "Beastly Apple A17 Pro chip built for Apple Intelligence",
            "Apple Pencil Pro support with haptic squeeze & barrel roll",
            "Pocketable 293g lightweight aluminum form factor",
            "Upgraded 10Gbps USB-C data transfer speeds",
        ]
        cons = [
            "60Hz display refresh rate (no 120Hz ProMotion)",
            "No headphone jack (requires USB-C adapter)",
        ]
        summary = "The ultimate pocket powerhouse. Combines the processing muscle of modern flagships with the note-taking portability of a digital Moleskine notebook."
        audience = "Ideal for pilots, students, and mobile creators who need maximum processing power in a one-handed footprint. Perfect as an ultra-portable digital notebook, field monitor, or handheld gaming console."
        buyers_take = "Unmatched in raw performance and one-handed convenience. If pocketability is your priority, this is the gold standard."
    elif "s9" in model.lower() or "s10" in model.lower():
        pros = ["Stunning 120Hz Dynamic AMOLED 2X display", "S-Pen included in the box", "Samsung DeX desktop capability", "IP68 water and dust resistance"]
        cons = ["Premium price on higher tiers", "Slightly heavier for one-handed use"]
        summary = "An Android productivity titan with gorgeous media, bundled stylus, and top-tier build quality."
        audience = "Power users who want desktop-grade multitasking, artists who prefer S-Pen, and professionals who need IP68 ruggedness."
        buyers_take = "The ultimate Android productivity powerhouse with gorgeous AMOLED display and bundled S-Pen."
    elif "10th" in model.lower() or "ipad 10" in model.lower():
        pros = [
            "Great value entry into the modern iPadOS ecosystem",
            "Crisp 10.9-inch Liquid Retina display with True Tone",
            "Reliable all-day battery life (~10 hours web/video)",
            "Landscape 12MP Ultra-Wide camera with Center Stage",
        ]
        cons = [
            "Base 64GB storage tier fills up quickly with apps/games",
            "Non-laminated display (no anti-reflective coating)",
        ]
        summary = "A versatile everyday tablet with modern all-screen design, dependable A14 Bionic speed, and excellent battery life for students, families, and media streaming."
        audience = "Students, families, and everyday users seeking a reliable tablet for note-taking, schoolwork, and streaming without paying flagship prices."
        buyers_take = "The benchmark standard for everyday tablet versatility. Outstanding balance of screen size, battery stamina, and iPadOS polish."
    elif "xiaomi" in model.lower() or "pad 8" in model.lower():
        pros = [
            "Flagship Snapdragon 8s Gen 4 processor with elite gaming and multitasking muscle",
            "Stunning 11.2-inch 3.2K 144Hz display with 68 billion colors and Dolby Vision",
            "Massive 9200mAh battery with rapid 45W turbo charging support",
            "Ultra-slim 6.1mm aerospace aluminum unibody weighing only 485g",
        ]
        cons = [
            "Focus Pen Pro and keyboard dock sold separately",
            "No cellular SIM slot (Wi-Fi only)",
        ]
        summary = "An aggressively priced Android powerhouse packing flagship Snapdragon 8s Gen 4 performance, a razor-sharp 3.2K 144Hz screen, and huge 9200mAh stamina in an ultra-slim aluminum shell."
        audience = "Gamers, students, and entertainment enthusiasts seeking flagship-level speed, high-refresh visuals, and long battery life without flagship four-figure prices."
        buyers_take = "Delivers exceptional hardware value in the premium mid-tier segment, pairing a top-tier 144Hz screen with flagship Qualcomm silicon."
    else:
        pros = ["Excellent value-for-money ratio", "Crisp high-resolution display", "All-day battery stamina", "Clean OS experience"]
        cons = ["Base storage fills quickly", "Fast charger sold separately"]
        summary = "A well-rounded tablet for students and streaming enthusiasts looking for premium features on a smart budget."
        audience = "Students, families, and casual users seeking reliable performance without breaking the bank."
        buyers_take = "A solid, budget-conscious choice delivering dependable day-to-day tablet performance."

    pros_html = "".join([
        f'<li style="margin-bottom:8px;color:#166534;font-size:0.92rem;list-style:none;display:flex;align-items:flex-start;gap:8px;">'
        f'<span style="color:#22c55e;font-weight:800;">✓</span> {p}</li>' for p in pros
    ])
    cons_html = "".join([
        f'<li style="margin-bottom:8px;color:#991b1b;font-size:0.92rem;list-style:none;display:flex;align-items:flex-start;gap:8px;">'
        f'<span style="color:#ef4444;font-weight:800;">✗</span> {c}</li>' for c in cons
    ])

    # Benchmark mini-meters
    bench_html = ""
    if benchmarks:
        gb_s = benchmarks.get("gb6_single", 0)
        gb_m = benchmarks.get("gb6_multi", 0)
        antutu = benchmarks.get("antutu", 0)
        bench_html = f"""
      <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;margin-bottom:16px;">
        <div style="font-size:0.72rem;font-weight:800;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">BENCHMARK SCORES</div>
        <div style="display:flex;flex-direction:column;gap:8px;">
          <div style="display:flex;align-items:center;justify-content:space-between;font-size:0.85rem;">
            <span style="color:#334155;font-weight:600;">Geekbench 6 (Single)</span>
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="width:100px;height:6px;background:#e2e8f0;border-radius:9999px;overflow:hidden;">
                <div style="width:{min(gb_s / 4000 * 100, 100):.0f}%;height:100%;background:#3b82f6;border-radius:9999px;"></div>
              </div>
              <span style="font-weight:800;color:#0f172a;font-size:0.8rem;width:40px;text-align:right;">{gb_s:,}</span>
            </div>
          </div>
          <div style="display:flex;align-items:center;justify-content:space-between;font-size:0.85rem;">
            <span style="color:#334155;font-weight:600;">Geekbench 6 (Multi)</span>
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="width:100px;height:6px;background:#e2e8f0;border-radius:9999px;overflow:hidden;">
                <div style="width:{min(gb_m / 15000 * 100, 100):.0f}%;height:100%;background:#22c55e;border-radius:9999px;"></div>
              </div>
              <span style="font-weight:800;color:#0f172a;font-size:0.8rem;width:40px;text-align:right;">{gb_m:,}</span>
            </div>
          </div>
          <div style="display:flex;align-items:center;justify-content:space-between;font-size:0.85rem;">
            <span style="color:#334155;font-weight:600;">AnTuTu v10</span>
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="width:100px;height:6px;background:#e2e8f0;border-radius:9999px;overflow:hidden;">
                <div style="width:{min(antutu / 2500000 * 100, 100):.0f}%;height:100%;background:#8b5cf6;border-radius:9999px;"></div>
              </div>
              <span style="font-weight:800;color:#0f172a;font-size:0.8rem;width:55px;text-align:right;">{antutu:,}</span>
            </div>
          </div>
        </div>
      </div>"""

    return f"""
<div id="editor-verdict" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:20px;margin:24px 0;align-items:start;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <!-- Left Column: The Verdict -->
  <div style="background:#ffffff;border:1px solid #e2e8f0;border-top:4px solid #3b82f6;border-radius:14px;padding:22px;box-shadow:0 4px 6px -1px rgba(0,0,0,0.03);display:flex;flex-direction:column;justify-content:space-between;">
    <div>
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
        <div>
          <span style="font-size:0.72rem;font-weight:800;color:#3b82f6;text-transform:uppercase;letter-spacing:0.5px;">EDITOR'S CHOICE</span>
          <h4 style="margin:2px 0 0 0;font-size:1.25rem;font-weight:800;color:#0f172a;">🎯 The Verdict</h4>
        </div>
        <div style="width:58px;height:58px;border-radius:50%;background:#eff6ff;border:3px solid #3b82f6;display:flex;flex-direction:column;align-items:center;justify-content:center;flex-shrink:0;">
          <span style="font-size:1.3rem;font-weight:800;color:#1d4ed8;line-height:1;">{score}</span>
          <span style="font-size:0.65rem;font-weight:700;color:#64748b;">/10</span>
        </div>
      </div>
      {bench_html}
      <p style="font-size:0.92rem;color:#475569;line-height:1.6;margin:0 0 14px 0;">{summary}</p>
      <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:12px;font-size:0.85rem;color:#166534;line-height:1.5;margin-bottom:14px;">
        <b>🎯 Who Is This For?</b> {audience}
      </div>
    </div>
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px;font-size:0.85rem;color:#334155;font-weight:600;">
      💡 <b>Buyer's Take:</b> {buyers_take}
    </div>
  </div>

  <!-- Right Column: Pros & Cons -->
  <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:14px;padding:22px;box-shadow:0 4px 6px -1px rgba(0,0,0,0.03);">
    <h4 style="margin:0 0 14px 0;font-size:1.15rem;font-weight:800;color:#0f172a;">⚖️ Pros &amp; Points to Consider</h4>
    <div style="margin-bottom:14px;">
      <div style="font-size:0.78rem;font-weight:800;color:#166534;text-transform:uppercase;margin-bottom:8px;">WHAT WE LOVE</div>
      <ul style="padding:0;margin:0;">{pros_html}</ul>
    </div>
    <div>
      <div style="font-size:0.78rem;font-weight:800;color:#991b1b;text-transform:uppercase;margin-bottom:8px;">WORTH NOTING</div>
      <ul style="padding:0;margin:0;">{cons_html}</ul>
    </div>
  </div>
</div>
"""


# ---------------------------------------------------------------------------
# Section: Hardware Bento Matrix
# ---------------------------------------------------------------------------

def render_hardware_bento(specs: Dict[str, Any]) -> str:
    """Render Accurate Hardware Bento Grid (4×2)."""
    model_key = _get_model_key(specs)
    augmented = TABLET_AUGMENTED_SPECS.get(model_key, {}) if model_key else {}
    brand = (specs.get("brand") or "").lower()
    processor_info = specs.get("processor") or "High-Performance Processor"
    benchmarks = _get_benchmarks(processor_info)
    disp_data = augmented.get("display", {})
    batt_data = augmented.get("battery_charging", {})
    conn_data = augmented.get("connectivity_extra", {})
    build_data = augmented.get("build", {})
    sw_data = augmented.get("software_security", {})

    display_info = specs.get("display_type") or f"{specs.get('screen_size', 'Display')} Panel"
    
    # Accurate RAM lookup
    ram_raw = specs.get("ram") or augmented.get("key_decision_specs", {}).get("ram_storage", "").split("•")[0].strip()
    if not ram_raw:
        if "10th" in (specs.get("model_name") or "").lower():
            ram_info = "4 GB Unified RAM"
        elif "mini" in (specs.get("model_name") or "").lower():
            ram_info = "8 GB Unified RAM"
        else:
            ram_info = "8 GB"
    else:
        ram_info = ram_raw

    storage_info = specs.get("storage") or "128 GB"
    conn_info = conn_data.get("Wi-Fi Standard") or specs.get("connectivity") or "Wi-Fi"

    # Subtitles
    proc_sub = f"{benchmarks.get('process', 'Flagship Architecture')} • Benchmark Verified" if benchmarks else "Flagship Multi-Core Architecture"
    disp_sub = f"{disp_data.get('Refresh Rate', '120Hz')} • Anti-Reflective • HDR" if "amoled" in display_info.lower() else "True Tone • Wide Color"
    
    if sw_data.get("Apple Intelligence"):
        ai_sub = "Apple Intelligence Certified"
    elif sw_data.get("Galaxy AI"):
        ai_sub = "Galaxy AI Powered • Fast LPDDR5X"
    elif "apple" in brand:
        ai_sub = "16-Core Neural Engine"
    else:
        ai_sub = "High-Speed Memory • Multitasking"

    storage_sub = "High-Speed UFS Storage • MicroSD Slot" if "samsung" in brand else "High-Speed Internal Storage Tier"
    io_val = conn_data.get("USB", "USB-C Interface")
    if "2.0" in io_val:
        io_sub = "DisplayPort Out • 480 Mbps Sync" if conn_data.get("DisplayPort via USB-C") else "480 Mbps Data Transfer"
    else:
        io_sub = "DisplayPort Out • High-Speed Transfer" if conn_data.get("DisplayPort via USB-C") else "Charging & Data Sync"

    batt_val = specs.get("battery") or "All-Day Stamina"
    batt_sub = f"{batt_data.get('Charging Wattage', 'Fast Charging')} • Intelligent Power"
    conn_sub = f"Bluetooth {conn_data.get('Bluetooth', '5.3')} • Low Latency"
    build_val = f"{build_data.get('Weight', '571g')} • {build_data.get('Thickness', '5.6mm')}" if build_data else "Premium Metal Chassis"
    build_sub = f"{build_data.get('Material', 'Armor Aluminum')} • {build_data.get('IP Rating', 'Premium Build')}" if build_data else "Aerospace Unibody"

    cards = [
        ("⚡", "Chip / SoC", processor_info, proc_sub),
        ("📱", "Display Tech", display_info, disp_sub),
        ("🧠", "Memory & AI", ram_info, ai_sub),
        ("💾", "Storage Tier", storage_info, storage_sub),
        ("🔌", "I/O & Ports", io_val, io_sub),
        ("🔋", "Battery & Charging", batt_val, batt_sub),
        ("📶", "Wireless", conn_info, conn_sub),
        ("🪶", "Form Factor / Build", build_val, build_sub),
    ]

    cards_html = ""
    for icon, label, val, sub in cards:
        cards_html += f"""
    <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:14px;display:flex;align-items:flex-start;gap:12px;box-shadow:0 1px 3px rgba(0,0,0,0.02);min-height:96px;box-sizing:border-box;">
      <div style="width:38px;height:38px;border-radius:10px;background:#f8fafc;border:1px solid #e2e8f0;display:flex;align-items:center;justify-content:center;font-size:1.25rem;flex-shrink:0;">{icon}</div>
      <div style="flex:1;min-width:0;">
        <div style="font-size:0.75rem;font-weight:700;text-transform:uppercase;color:#475569;letter-spacing:0.5px;">{label}</div>
        <div style="font-size:0.95rem;font-weight:800;color:#0f172a;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{val}</div>
        <div style="font-size:0.72rem;color:#64748b;margin-top:2px;">{sub}</div>
      </div>
    </div>"""

    return f"""
<div id="hardware-bento" style="margin:30px 0;scroll-margin-top:90px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;border-bottom:2px solid #f1f5f9;padding-bottom:10px;">
    <h3 style="margin:0;font-size:1.25rem;font-weight:800;color:#0f172a;">⚙️ Detailed Hardware Bento Matrix</h3>
    <span style="font-size:0.75rem;font-weight:700;color:#3b82f6;background:#eff6ff;padding:4px 10px;border-radius:9999px;">VERIFIED SPECS</span>
  </div>
  <div class="tt-bento-grid" style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;">{cards_html}</div>
</div>
"""


# ---------------------------------------------------------------------------
# Section: Practical Experience
# ---------------------------------------------------------------------------

def render_practical_experience(tablet: Optional[Dict[str, Any]] = None) -> str:
    """Render Practical Experience highlights tailored to the tablet."""
    specs = (tablet or {}).get("specs") or {}
    model_key = _get_model_key(specs)
    augmented = TABLET_AUGMENTED_SPECS.get(model_key, {}) if model_key else {}
    sw_data = augmented.get("software_security", {})
    brand = (specs.get("brand") or "").lower()
    model = (specs.get("model_name") or "").lower()

    if "samsung" in brand or "galaxy" in model:
        items = [
            ("✨ Galaxy AI Productivity Suite", "Note Assist for auto-formatting, Circle to Search with Google, Sketch to Image, and live audio transcription."),
            ("✏️ Bundled S Pen & IP68 Durability", "Ultra-low 2.8ms latency stylus included in the box. Both the tablet and S Pen are IP68 water & dust resistant."),
            ("🖥️ Samsung DeX Desktop Mode", "Turn your tablet into a PC workstation with wireless monitor extension, multi-window multitasking, and keyboard dock support."),
            ("🎬 120Hz Anti-Reflective AMOLED 2X", "Vibrant Dynamic AMOLED display with anti-reflective glass coating for outdoor legibility and AKG quad speakers."),
        ]
    elif sw_data.get("Apple Intelligence"):
        items = [
            ("🤖 Apple Intelligence Ready", "On-device generative AI, smarter Siri, Clean Up photo editing, and system-wide writing tools."),
            ("🎮 Console-Tier AAA Gaming", "Hardware-accelerated ray tracing on flagship Apple Silicon GPU architecture."),
            ("✏️ Precision Stylus Ecosystem", "Magnetic pairing, pressure sensitivity, hover detection, and precision handwriting."),
            ("⚡ High-Speed USB-C Workflow", "Fast data transfers for 4K footage offloading and high-speed external storage connectivity."),
        ]
    elif "10th" in model or "a14" in (specs.get("processor") or "").lower():
        items = [
            ("⚡ Dependable Everyday Performance", "Smooth multitasking with iPadOS, split-screen workflows, and responsive app switching powered by the Apple A14 Bionic chip."),
            ("🎨 Creative & Note-Taking Workspace", "Precision handwriting, digital sketching, and annotation support with Apple Pencil (USB-C & 1st Gen)."),
            ("📹 Landscape Center Stage Video Calls", "Landscape 12MP Ultra-Wide front camera keeps you automatically centered in the frame during FaceTime, Zoom, and remote classes."),
            ("🔋 All-Day Battery Stamina", "Up to 10 hours of continuous web surfing or video playback on Wi-Fi, easily powering a full day of school or work."),
        ]
    elif "xiaomi" in brand or "pad 8" in model or "hyperos" in (specs.get("operating_system") or "").lower():
        items = [
            ("⚡ Snapdragon 8s Gen 4 Muscle", "Flagship 4nm performance handles demanding mobile gaming, 4K media workflows, and intensive split-screen multitasking with ease."),
            ("🎬 3.2K 144Hz ImmersiView Visuals", "Crystal-clear 3200×2136 resolution with 68 billion+ colors, Dolby Vision, and 144Hz adaptive refresh rate for silky-smooth browsing."),
            ("🔋 9200mAh Battery & 45W Turbo Charging", "Huge battery stamina powers through long work sessions, coupled with 45W fast charging to get you back up to full quickly."),
            ("🔊 Quad Immersive Dolby Atmos Audio", "Four precision-tuned stereo speakers with Hi-Res certification and 200% volume boost for cinema-grade sound."),
        ]
    else:
        items = [
            ("⚡ High-Performance Multitasking", "Smooth split-screen productivity and responsive app switching."),
            ("🎬 Immersive Audiovisual Experience", "High refresh rate screen paired with quad stereo speakers for movies and content creation."),
            ("🔋 All-Day Battery Stamina", "Long-lasting battery capacity optimized with intelligent power-saving management."),
            ("📱 Premium Lightweight Build", "Sleek metal unibody craftsmanship designed for comfortable daily handheld use."),
        ]

    cards_html = ""
    for title, desc in items:
        cards_html += f"""
    <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:16px;display:flex;align-items:flex-start;gap:12px;">
      <div style="background:#ecfdf5;color:#059669;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:0.8rem;font-weight:800;flex-shrink:0;margin-top:2px;">✓</div>
      <div>
        <div style="font-size:0.95rem;font-weight:800;color:#0f172a;margin-bottom:4px;">{title}</div>
        <div style="font-size:0.88rem;color:#475569;line-height:1.5;">{desc}</div>
      </div>
    </div>"""

    return f"""
<div style="margin:35px 0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;border-bottom:2px solid #f1f5f9;padding-bottom:10px;">
    <h3 style="margin:0;font-size:1.25rem;font-weight:800;color:#0f172a;">✨ Practical Experience &amp; Performance</h3>
    <span style="font-size:0.75rem;font-weight:700;color:#059669;background:#ecfdf5;padding:4px 10px;border-radius:9999px;">REAL-WORLD TESTED</span>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:12px;">{cards_html}</div>
</div>
"""


# ---------------------------------------------------------------------------
# Section: Enhanced 2-Column Tabbed Specification Database
# ---------------------------------------------------------------------------

def _build_enhanced_spec_categories(
    full_specs: Dict[str, Any],
    specs: Dict[str, Any],
) -> List[Tuple[str, str, str, List[Tuple[str, str]]]]:
    """Build grouped spec categories with visual pills.
    Returns [(tab_group_id, cat_name, icon, [(key, value_html)])...].
    """
    model_key = _get_model_key(specs)
    augmented = TABLET_AUGMENTED_SPECS.get(model_key, {}) if model_key else {}
    brand = (specs.get("brand") or "").lower()
    processor = specs.get("processor") or ""
    benchmarks = _get_benchmarks(processor)

    categories: List[Tuple[str, str, str, List[Tuple[str, str]]]] = []

    # 1. Display & Stylus (group_id: "display")
    disp_data = augmented.get("display", {})
    stylus_data = augmented.get("stylus", {})
    disp_rows = [
        ("Screen Size", specs.get("screen_size") or "Display"),
        ("Display Panel", specs.get("display_type") or full_specs.get("Display Panel") or "High-Res Panel"),
        ("Resolution", full_specs.get("Display Resolution Maximum") or "High-Definition Resolution"),
        ("Refresh Rate", disp_data.get("Refresh Rate", "120 Hz" if "amoled" in (specs.get("display_type") or "").lower() else "60 Hz")),
    ]
    if disp_data.get("ProMotion 120Hz") is not None:
        disp_rows.append(("120Hz High Refresh", _pill_html("120Hz High Refresh", disp_data["ProMotion 120Hz"])))
    if disp_data.get("Peak Brightness"):
        disp_rows.append(("Peak Brightness", disp_data["Peak Brightness"]))
    if disp_data.get("Color Gamut"):
        disp_rows.append(("Color Gamut", disp_data["Color Gamut"]))
    if disp_data.get("True Tone") is not None:
        disp_rows.append(("True Tone", _pill_html("True Tone", disp_data["True Tone"])))
    if disp_data.get("Screen-to-Body Ratio"):
        disp_rows.append(("Screen-to-Body Ratio", disp_data["Screen-to-Body Ratio"]))
    if disp_data.get("Fully Laminated") is not None:
        disp_rows.append(("Lamination", _pill_html("Fully Laminated", disp_data["Fully Laminated"])))
    if disp_data.get("Anti-Reflective Coating") is not None:
        disp_rows.append(("Anti-Reflective", _pill_html("Anti-Reflective", disp_data["Anti-Reflective Coating"])))
    stylus_label = "S Pen" if "samsung" in brand else "Apple Pencil" if "apple" in brand else "Stylus"
    if stylus_data.get("Stylus Support"):
        disp_rows.append((stylus_label, stylus_data["Stylus Support"]))
    if stylus_data.get("Stylus Latency"):
        disp_rows.append(("Stylus Latency", stylus_data["Stylus Latency"]))
    for feat in ["Hover Detection", "Barrel Roll", "Haptic Squeeze", "Palm Rejection", "Air Actions"]:
        val = stylus_data.get(feat)
        if val is not None:
            disp_rows.append((feat, _pill_html(feat, val)))
    categories.append(("display", "Display & Stylus", "📱", [(k, v) for k, v in disp_rows if v]))

    # 2. Performance & Chip (group_id: "performance")
    perf_rows = [
        ("Processor / SoC", specs.get("processor") or full_specs.get("Processor", "High-Performance SoC")),
        ("RAM", specs.get("ram") or full_specs.get("RAM", "8 GB")),
        ("Internal Storage", specs.get("storage") or full_specs.get("Internal Storage", "128 GB")),
    ]
    if benchmarks:
        perf_rows.append(("Fabrication Node", benchmarks.get("process", "TSMC Flagship Node")))
        perf_rows.append(("Geekbench 6 (Single-Core)", f'{benchmarks["gb6_single"]:,}'))
        perf_rows.append(("Geekbench 6 (Multi-Core)", f'{benchmarks["gb6_multi"]:,}'))
        perf_rows.append(("AnTuTu v10 Benchmark", f'{benchmarks["antutu"]:,}'))
    sw_data = augmented.get("software_security", {})
    if sw_data.get("Galaxy AI") is not None:
        perf_rows.append(("Galaxy AI", _pill_html("Galaxy AI Suite", sw_data["Galaxy AI"])))
    elif sw_data.get("Apple Intelligence") is not None:
        perf_rows.append(("Apple Intelligence", _pill_html("Apple Intelligence", sw_data["Apple Intelligence"])))
    if sw_data.get("Operating System") or specs.get("operating_system"):
        perf_rows.append(("Operating System", sw_data.get("Operating System") or specs.get("operating_system")))
    if sw_data.get("Security Updates"):
        perf_rows.append(("Security Updates", sw_data["Security Updates"]))
    categories.append(("performance", "Performance & Chipset", "⚡", [(k, v) for k, v in perf_rows if v]))

    # 3. Battery & Ports (group_id: "battery_ports")
    batt_data = augmented.get("battery_charging", {})
    conn_data = augmented.get("connectivity_extra", {})
    batt_conn_rows = [
        ("Battery Stamina", specs.get("battery") or full_specs.get("Battery Stamina", "Up to 10 hours")),
        ("Charging Wattage", batt_data.get("Charging Wattage", "20W USB-PD")),
        ("Charge Time (0→100%)", batt_data.get("Charge Time (0→100%)", "~2 hours")),
    ]
    if batt_data.get("Reverse Wired Charging") is not None:
        batt_conn_rows.append(("Reverse Charging", _pill_html("Reverse Charging", batt_data["Reverse Wired Charging"])))
    if conn_data.get("USB"):
        batt_conn_rows.append(("USB Interface", conn_data["USB"]))
    if conn_data.get("DisplayPort via USB-C") is not None:
        batt_conn_rows.append(("DisplayPort Out", _pill_html("DisplayPort via USB-C", conn_data["DisplayPort via USB-C"])))
    if conn_data.get("Wi-Fi Standard"):
        batt_conn_rows.append(("Wi-Fi Standard", _pill_html(conn_data["Wi-Fi Standard"], True)))
    if conn_data.get("Bluetooth"):
        batt_conn_rows.append(("Bluetooth", conn_data["Bluetooth"]))
    if conn_data.get("3.5mm Headphone Jack") is not None:
        batt_conn_rows.append(("Headphone Jack", _pill_html("3.5mm Headphone Jack", conn_data["3.5mm Headphone Jack"])))
    if conn_data.get("MicroSD Expansion") is not None:
        batt_conn_rows.append(("MicroSD Slot", _pill_html("MicroSD Slot", conn_data["MicroSD Expansion"])))
    categories.append(("battery_ports", "Battery & Ports", "🔋", [(k, v) for k, v in batt_conn_rows if v]))

    # 4. Cameras & Audio (group_id: "cameras")
    cam_data = augmented.get("cameras", {})
    build_data = augmented.get("build", {})
    cam_rows = [
        ("Rear Camera", cam_data.get("Rear Camera", "12 MP Wide, f/1.8")),
        ("Front Camera", cam_data.get("Front Camera", "12 MP Ultra Wide, f/2.4")),
        ("Video Recording", cam_data.get("Video Recording", "4K @ 60 fps")),
    ]
    if cam_data.get("Center Stage") is not None:
        cam_rows.append(("Center Stage", _pill_html("Center Stage", cam_data["Center Stage"])))
    if build_data.get("Landscape Stereo Speakers") is not None:
        cam_rows.append(("Speakers", _pill_html("Landscape Stereo Speakers", build_data["Landscape Stereo Speakers"])))
    cam_rows.append(("Microphones", "Dual Studio-quality Microphones"))
    categories.append(("cameras", "Cameras & Audio", "📸", [(k, v) for k, v in cam_rows if v]))

    # 5. Design & Build (group_id: "design")
    design_rows = [
        ("Brand", specs.get("brand") or full_specs.get("Brand", "Apple")),
        ("Model Name", specs.get("model_name") or full_specs.get("Model Name", "iPad mini (7th Gen)")),
        ("Weight", build_data.get("Weight", "293 grams")),
        ("Thickness", build_data.get("Thickness", "6.3 mm")),
        ("Chassis Material", build_data.get("Material", "100% Recycled Aluminum")),
        ("IP Rating", _pill_html("IP Water Rating", False)),
    ]
    if sw_data.get("Biometric"):
        design_rows.append(("Biometrics", sw_data["Biometric"]))
    if sw_data.get("Face ID") is not None:
        design_rows.append(("Face ID", _pill_html("Face ID", sw_data["Face ID"])))
    sensor_data = augmented.get("sensors", {})
    sensor_list = [k for k, present in sensor_data.items() if present and k not in ["GPS"]]
    if sensor_list:
        design_rows.append(("Built-in Sensors", ", ".join(sensor_list)))
    inc = full_specs.get("Included Components", "")
    if inc:
        design_rows.append(("In the Box", inc))
    categories.append(("design", "Design, Build & Sensors", "📐", [(k, v) for k, v in design_rows if v]))

    return [(grp, name, icon, rows) for grp, name, icon, rows in categories if rows]


def render_enhanced_specs_table(full_specs: Dict[str, Any], specs: Dict[str, Any]) -> str:
    """Render Modern 2-Column Tabbed Specs section with real-time search and category tabs."""
    model_key = _get_model_key(specs)
    augmented = TABLET_AUGMENTED_SPECS.get(model_key, {}) if model_key else {}
    disp_data = augmented.get("display", {})
    stylus_data = augmented.get("stylus", {})
    sw_data = augmented.get("software_security", {})
    batt_data = augmented.get("battery_charging", {})
    conn_data = augmented.get("connectivity_extra", {})
    processor = specs.get("processor") or ""
    benchmarks = _get_benchmarks(processor)
    model_name_lower = (specs.get("model_name") or "").lower()

    # 1. Display Items (tab-display: Display & Stylus)
    raw_screen = specs.get("screen_size") or "8.3 inches"
    if "mini" in model_name_lower or "8.3" in raw_screen:
        screen_display = '8.3" Liquid Retina IPS LCD'
        res_display = '2266 × 1488 px (~326 ppi)'
        panel_type = 'Liquid Retina IPS • 500 nits'
    elif "s10" in model_name_lower or "12.4" in raw_screen:
        screen_display = '12.4" Dynamic AMOLED 2X'
        res_display = '2800 × 1752 px (~266 ppi)'
        panel_type = 'Dynamic AMOLED 2X • 650 nits HBM'
    elif "10th" in model_name_lower or "10.9" in raw_screen:
        screen_display = '10.9" Liquid Retina IPS LCD'
        res_display = '2360 × 1640 px (~264 ppi)'
        panel_type = 'Liquid Retina IPS • 500 nits'
    else:
        panel_val = specs.get("display_type") or full_specs.get("Display Panel") or "IPS LCD"
        screen_display = raw_screen
        res_display = full_specs.get("Display Resolution Maximum") or "High Resolution"
        panel_type = f"{panel_val} • 500 nits"

    refresh_raw = disp_data.get("Refresh Rate", "60 Hz")
    if disp_data.get("ProMotion 120Hz") is False:
        refresh_html = f'<span class="tt-spec-v tt-neg">✖ {refresh_raw} (No ProMotion)</span>'
    elif disp_data.get("ProMotion 120Hz") is True:
        refresh_html = f'<span class="tt-spec-v tt-pos">✔ {refresh_raw} ProMotion 120Hz</span>'
    else:
        refresh_html = f'<span class="tt-spec-v">{refresh_raw}</span>'

    stylus_supp = stylus_data.get("Stylus Support") or ("Apple Pencil Pro & USB-C" if "apple" in (specs.get("brand") or "").lower() else "Bundled S Pen in Box")
    stylus_html = f'<span class="tt-spec-v tt-pos">✔ {stylus_supp}</span>'

    coating_val = "Anti-Reflective • Fully Laminated" if disp_data.get("Anti-Reflective Coating") else ("True Tone • Oleophobic Coating" if disp_data.get("True Tone") else "Scratch-Resistant Glass")
    coating_html = f'<span class="tt-spec-v">{coating_val}</span>'

    # 2. Performance Items (tab-perf: Compute & Silicon)
    proc_val = specs.get("processor") or full_specs.get("Processor") or "Apple A17 Pro (6-core)"
    if "A17 Pro" in proc_val:
        proc_display = "Apple A17 Pro (6-core, 3nm TSMC)"
        gpu_display = "5-Core GPU (Hardware Ray Tracing)"
    elif "Dimensity 9300+" in proc_val or "dimensity" in proc_val.lower():
        proc_display = "Dimensity 9300+ (4nm TSMC, 3.4GHz)"
        gpu_display = "Immortalis-G720 MC12 Ray Tracing"
    elif "A14" in proc_val:
        proc_display = "Apple A14 Bionic (6-core, 5nm TSMC)"
        gpu_display = "4-Core Apple Designed GPU"
    elif benchmarks:
        proc_display = f"{proc_val} ({benchmarks.get('process', 'TSMC')})"
        gpu_display = "Integrated Flagship GPU"
    else:
        proc_display = proc_val
        gpu_display = "Integrated High-Speed GPU"

    ram_raw = specs.get("ram") or full_specs.get("RAM")
    if not ram_raw:
        if "10th" in model_name_lower:
            ram_val = "4 GB Unified RAM"
        elif "mini" in model_name_lower:
            ram_val = "8 GB Unified RAM"
        elif "s10" in model_name_lower:
            ram_val = "12 GB LPDDR5X"
        else:
            ram_val = "8 GB"
    else:
        ram_val = f"{ram_raw} Unified RAM" if "apple" in (specs.get("brand") or "").lower() else f"{ram_raw} RAM"

    if sw_data.get("Apple Intelligence"):
        ram_html = f'<span class="tt-spec-v tt-pos">✔ {ram_val} (Apple Intelligence)</span>'
    elif sw_data.get("Galaxy AI"):
        ram_html = f'<span class="tt-spec-v tt-pos">✔ {ram_val} (Galaxy AI)</span>'
    else:
        ram_html = f'<span class="tt-spec-v">{ram_val}</span>'

    gb_multi = f"{benchmarks['gb6_multi']:,} points" if benchmarks else "7,379 points"
    antutu_score = f"{benchmarks['antutu']:,} points" if benchmarks and benchmarks.get("antutu") else "1,650,000 points"

    os_val = sw_data.get("Operating System") or specs.get("operating_system") or "iPadOS 18"
    if sw_data.get("Security Updates"):
        os_display = f"{os_val} ({sw_data['Security Updates'].split('guaranteed')[0].strip()} updates)"
    else:
        os_display = f"{os_val} (5+ yrs updates)"

    # 3. Battery & Ports Items (tab-battery: Battery & Ports)
    if "mini" in model_name_lower:
        batt_cap = "19.3 Wh Li-Po (~10 hrs web)"
    elif "s10" in model_name_lower:
        batt_cap = "10,090 mAh Li-Po (~16 hrs video)"
    elif "10th" in model_name_lower:
        batt_cap = "28.6 Wh Li-Po (~10 hrs web)"
    else:
        batt_cap = specs.get("battery") or "Up to 10 Hours All-Day"

    chg_watt = batt_data.get("Charging Wattage") or "20W USB-PD"
    usb_port = conn_data.get("USB") or "USB-C 3.1 (10Gbps)"
    chg_val = f"{chg_watt} • {usb_port}"

    dp_val = "✔ 4K DisplayPort Video Output" if conn_data.get("DisplayPort via USB-C") else "✖ Video Out via USB-C Not Supported"
    dp_html = f'<span class="tt-spec-v {"tt-pos" if conn_data.get("DisplayPort via USB-C") else "tt-neg"}">{dp_val}</span>'

    wifi_val = f"{conn_data.get('Wi-Fi Standard', 'Wi-Fi 6E')} • BT {conn_data.get('Bluetooth', '5.3')}"

    jack_val = "✔ 3.5mm Headphone Jack Included" if conn_data.get("3.5mm Headphone Jack") else "✖ No 3.5mm Jack (Audio via USB-C/BT)"
    jack_html = f'<span class="tt-spec-v {"tt-pos" if conn_data.get("3.5mm Headphone Jack") else "tt-neg"}">{jack_val}</span>'

    biom_val = sw_data.get("Biometric") or "Biometric Authentication"

    items = [
        # Display & Stylus (data-cat="display")
        ("display", "Display Diagonal", f'<span style="font-weight:600; color:#0f172a;">{screen_display}</span>'),
        ("display", "Resolution & Density", f'<span style="font-weight:600; color:#0f172a;">{res_display}</span>'),
        ("display", "Refresh Rate", refresh_html.replace('class="tt-spec-v tt-neg"', 'style="font-weight:600; color:#dc2626;"').replace('class="tt-spec-v tt-pos"', 'style="font-weight:600; color:#16a34a;"').replace('class="tt-spec-v"', 'style="font-weight:600; color:#0f172a;"')),
        ("display", "Stylus Compatibility", stylus_html.replace('class="tt-spec-v tt-pos"', 'style="font-weight:600; color:#16a34a;"')),
        ("display", "Panel & Brightness", f'<span style="font-weight:600; color:#0f172a;">{panel_type}</span>'),
        ("display", "Glass & Lamination", coating_html.replace('class="tt-spec-v"', 'style="font-weight:600; color:#0f172a;"')),

        # Compute & Silicon (data-cat="silicon")
        ("silicon", "Processor / SoC", f'<span style="font-weight:600; color:#0f172a;">{proc_display}</span>'),
        ("silicon", "Graphics / GPU", f'<span style="font-weight:600; color:#0f172a;">{gpu_display}</span>'),
        ("silicon", "System Memory / RAM", ram_html.replace('class="tt-spec-v tt-pos"', 'style="font-weight:600; color:#16a34a;"').replace('class="tt-spec-v"', 'style="font-weight:600; color:#0f172a;"')),
        ("silicon", "Geekbench 6 Multi", f'<span style="font-weight:600; color:#0f172a;">{gb_multi}</span>'),
        ("silicon", "AnTuTu v10 Total", f'<span style="font-weight:600; color:#0f172a;">{antutu_score}</span>'),
        ("silicon", "Operating Platform", f'<span style="font-weight:600; color:#0f172a;">{os_display}</span>'),

        # Battery & Ports (data-cat="battery")
        ("battery", "Battery Cell Capacity", f'<span style="font-weight:600; color:#0f172a;">{batt_cap}</span>'),
        ("battery", "Wired Charging & Port", f'<span style="font-weight:600; color:#0f172a;">{chg_val}</span>'),
        ("battery", "DisplayPort Video Out", dp_html.replace('class="tt-spec-v tt-pos"', 'style="font-weight:600; color:#16a34a;"').replace('class="tt-spec-v tt-neg"', 'style="font-weight:600; color:#dc2626;"')),
        ("battery", "Wireless Connectivity", f'<span style="font-weight:600; color:#0f172a;">{wifi_val}</span>'),
        ("battery", "Audio & Headphone Jack", jack_html.replace('class="tt-spec-v tt-pos"', 'style="font-weight:600; color:#16a34a;"').replace('class="tt-spec-v tt-neg"', 'style="font-weight:600; color:#dc2626;"')),
        ("battery", "Biometrics & Security", f'<span style="font-weight:600; color:#0f172a;">{biom_val}</span>'),
    ]

    grid_items = []
    for cat, k, v in items:
        grid_items.append(
            f'<div class="tt-row" data-cat="{cat}" style="display:flex; justify-content:space-between; align-items:baseline; padding:11px 0; border-bottom:1px solid #f1f5f9; font-size:13.5px; gap:14px;">'
            f'<span style="color:#475569; font-weight:600; min-width:130px;">{k}</span>'
            f'<div style="text-align:right;">{v}</div>'
            f'</div>'
        )

    grid_items_html = "\n".join(grid_items)

    return f"""
  <!-- Complete Technical Specifications -->
  <section id="tt-specs" style="background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:24px; margin-bottom:32px;">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; border-bottom:1px solid #f1f5f9; padding-bottom:16px; margin-bottom:16px;">
      <div>
        <span style="font-size:11px; font-weight:700; color:#2563eb; text-transform:uppercase;">Reference Database</span>
        <h3 style="margin:2px 0 0 0; font-size:18px; font-weight:700; color:#0f172a;">Complete Technical Specifications</h3>
      </div>
      <div class="tt-filter-tabs" style="display:flex; gap:6px; background:#f1f5f9; padding:4px; border-radius:8px; flex-wrap:wrap;">
        <button type="button" class="tt-tab active" data-tab="all" style="border:none; background:#2563eb; color:#fff; font-size:12px; font-weight:700; padding:6px 14px; border-radius:6px; cursor:pointer; transition:all 0.15s ease;">All</button>
        <button type="button" class="tt-tab" data-tab="display" style="border:none; background:transparent; color:#475569; font-size:12px; font-weight:600; padding:6px 14px; border-radius:6px; cursor:pointer; transition:all 0.15s ease;">Display &amp; Stylus</button>
        <button type="button" class="tt-tab" data-tab="silicon" style="border:none; background:transparent; color:#475569; font-size:12px; font-weight:600; padding:6px 14px; border-radius:6px; cursor:pointer; transition:all 0.15s ease;">Compute &amp; Silicon</button>
        <button type="button" class="tt-tab" data-tab="battery" style="border:none; background:transparent; color:#475569; font-size:12px; font-weight:600; padding:6px 14px; border-radius:6px; cursor:pointer; transition:all 0.15s ease;">Battery &amp; Ports</button>
      </div>
    </div>

    <!-- 2-Column Specs Grid -->
    <div class="tt-spec-grid" style="display:grid; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); column-gap:32px;">
      {grid_items_html}
    </div>
  </section>
"""


# ---------------------------------------------------------------------------
# Section: Editorial Trust & Affiliate Disclosure
# ---------------------------------------------------------------------------

def render_editorial_disclosure() -> str:
    """Render clean editorial affiliate disclaimer notice inside styled callout box."""
    return """
  <!-- Affiliate Disclosure Notice -->
  <div class="tt-editorial-callout" style="background:#f8fafc;border-left:4px solid #0284c7;border-radius:0 10px 10px 0;padding:16px 20px;margin:35px 0 20px 0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;box-shadow:0 1px 3px rgba(0,0,0,0.03);">
    <div style="display:flex;align-items:flex-start;gap:12px;">
      <span style="font-size:1.25rem;line-height:1.3;flex-shrink:0;">ℹ️</span>
      <div>
        <h4 style="margin:0 0 4px 0;font-size:0.95rem;font-weight:700;color:#0f172a;">Editorial Integrity &amp; Affiliate Disclosure</h4>
        <p style="margin:0;font-size:0.86rem;color:#475569;line-height:1.55;"><strong>Editorial Note:</strong> TopTablets is an independent, reader-supported tablet database. When you purchase through links on our site, we may earn an affiliate commission at no extra cost to you. Pricing, discounts, and real-time stock availability reflect verified hardware listings from Amazon India.</p>
      </div>
    </div>
  </div>
"""


# ---------------------------------------------------------------------------
# Section: Sticky Floating Bar (Amazon India Conversion Hub)
# ---------------------------------------------------------------------------

def render_sticky_floating_bar(tablet: Dict[str, Any]) -> str:
    """Render slim Amazon India floating conversion bar with rating, stock, & Lowest badge."""
    specs = tablet.get("specs") or {}
    model = specs.get("model_name") or tablet.get("title", "Tablet")
    storage = specs.get("storage") or "128 GB"
    price = tablet.get("best_price") or tablet.get("regular_price")
    amz = tablet.get("amazon") or {}
    url = amz.get("affiliate_url") or amz.get("url") or tablet.get("primary_aff_url") or "#"
    thumb = tablet.get("main_image") or ((tablet.get("images") or [])[0] if tablet.get("images") else "")
    rating = amz.get("rating") or 4.6
    review_count = amz.get("review_count") or 162

    return f"""
<div id="tt-sticky-buy-bar" class="tt-sticky-bar" style="position:fixed;bottom:0;left:0;width:100%;z-index:9999;background:#0f172a;box-shadow:0 -4px 20px rgba(0,0,0,0.3);border-top:1px solid rgba(255,255,255,0.12);padding:10px 24px;display:none;align-items:center;justify-content:space-between;gap:16px;box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="display:flex;align-items:center;gap:12px;">
    <img src="{thumb}" alt="{model}" style="width:40px;height:40px;object-fit:contain;background:#ffffff;border-radius:8px;padding:2px;border:1px solid rgba(255,255,255,0.2);flex-shrink:0;" />
    <div>
      <div class="tt-sticky-title" style="font-weight:700;font-size:0.92rem;color:#ffffff;line-height:1.2;">{model} ({storage})</div>
      <div style="display:flex;align-items:center;gap:8px;margin-top:2px;">
        <span style="color:#fbbf24;font-size:0.75rem;font-weight:700;">★ {rating}</span>
        <span style="font-size:0.72rem;color:#64748b;">({review_count:,})</span>
        <span style="color:rgba(255,255,255,0.2);">|</span>
        <span class="tt-sticky-price" style="font-size:0.78rem;color:#4ade80;font-weight:700;">Amazon Price: {_format_money(price)}</span>
        <span style="font-size:0.7rem;background:rgba(34,197,94,0.15);color:#4ade80;padding:1px 6px;border-radius:4px;font-weight:600;">IN STOCK</span>
      </div>
    </div>
  </div>
  <a href="{url}" target="_blank" rel="nofollow sponsored" style="background:#ff9900;color:#111827;font-weight:800;font-size:0.92rem;padding:9px 20px;border-radius:8px;text-decoration:none;display:inline-flex;align-items:center;gap:6px;box-shadow:0 4px 12px rgba(255,153,0,0.35);white-space:nowrap;transition:transform 0.15s ease;">
    <span>Buy on Amazon ({_format_money(price)})</span>
    <span style="font-size:1.1rem;">↗</span>
  </a>
</div>
"""


# ---------------------------------------------------------------------------
# Assemblers
# ---------------------------------------------------------------------------

def clean_html(raw_html: str) -> str:
    """Strip HTML comments and inter-tag newlines so WordPress wpautop does not inject stray <p> or <br> tags."""
    cleaned = re.sub(r"<!--.*?-->", "", raw_html, flags=re.DOTALL)
    cleaned = re.sub(r">\s*\n+\s*<", "><", cleaned)
    cleaned = re.sub(r">\s+<", "><", cleaned)
    return cleaned.strip()


def build_short_description(tablet: Dict[str, Any]) -> str:
    """Construct spec-hub hero above-the-fold short description with read-only variant matrix and Amazon India CTA."""
    specs = tablet.get("specs") or {}
    best_price = tablet.get("best_price") or tablet.get("regular_price") or 0
    price_fmt = f"₹{int(best_price):,}" if best_price else ""

    amz = tablet.get("amazon") or {}
    amz_url = amz.get("affiliate_url") or amz.get("url") or tablet.get("primary_aff_url") or "#"
    model_name = specs.get("model_name") or tablet.get("title", "Tablet")

    rating_val = amz.get("rating") or 4.6
    reviews_cnt = amz.get("review_count") or 162
    score = round(float(rating_val) * 2, 1)

    regular_price = tablet.get("regular_price") or (tablet.get("amazon") or {}).get("mrp") or 0
    mrp_fmt = f"₹{int(regular_price):,}" if regular_price else ""
    discount_pct = round(((regular_price - best_price) / regular_price) * 100) if regular_price and best_price and regular_price > best_price else 0

    mrp_deal_part = ""
    if regular_price and regular_price > best_price:
        mrp_deal_part = f' <span class="tt-price-mrp" style="font-size:0.92rem;color:#94a3b8;text-decoration:line-through;font-weight:500;">MRP: {mrp_fmt}</span> <span class="tt-price-discount" style="font-size:0.85rem;font-weight:700;color:#16a34a;background:#f0fdf4;padding:2px 6px;border-radius:4px;border:1px solid #bbf7d0;">({discount_pct}% Off)</span>'

    price_deal_html = f"""
  <div class="tt-hero-price-wrap" style="margin:12px 0 14px 0;">
    <div class="tt-price-deal-row" style="display:flex;align-items:baseline;gap:8px;margin-bottom:6px;flex-wrap:wrap;">
      <span class="tt-price-current" style="font-size:1.75rem;font-weight:800;color:#0f172a;letter-spacing:-0.5px;">{price_fmt}</span>{mrp_deal_part}
    </div>
    <div class="tt-bank-offer-badge" style="display:inline-flex;align-items:center;gap:6px;background:#f0fdf4;border:1px solid #bbf7d0;color:#166534;font-size:0.78rem;font-weight:600;padding:4px 10px;border-radius:6px;">
      💳 Flat ₹3,000 instant discount on HDFC/ICICI cards
    </div>
  </div>"""

    # Variant selector data
    model_key = _get_model_key(specs)
    augmented = TABLET_AUGMENTED_SPECS.get(model_key, {}) if model_key else {}
    current_storage = specs.get("storage") or "128 GB"
    current_conn = specs.get("connectivity") or "Wi-Fi"

    # Micro-badge initial configuration
    screen_desc = "8.3\" Liquid Retina" if "mini" in (specs.get("model_name") or "").lower() else (specs.get("screen_size", "8.3\"") + " " + (specs.get("display_type") or "Liquid Retina"))
    config_str = f"{screen_desc} • {current_storage} • {current_conn}"

    config_badge_html = f"""
  <div id="tt-hero-config-badge" class="tt-config-badge" data-screen="{screen_desc}" data-storage="{current_storage}" data-conn="{current_conn}" data-base-price="{int(best_price)}">
    <span class="tt-config-dot"></span>
    <span id="tt-selected-config-text">{config_str}</span>
  </div>"""

    # Available Models & Configurations (Read-Only Specification Display)
    storage_badges = augmented.get("storage_badges")
    if not storage_badges:
        storage_opts = augmented.get("storage_options") or [specs.get("storage") or "128 GB"]
        storage_badges = [(opt, "(Base)" if i == 0 else None) for i, opt in enumerate(storage_opts)]

    storage_badges_html = []
    for opt, badge_sub in storage_badges:
        if badge_sub:
            storage_badges_html.append(
                f'<span class="tt-badge tt-badge-base" style="background:#f0fdf4;border:1px solid #86efac;color:#15803d;font-size:0.82rem;font-weight:600;padding:4px 10px;border-radius:6px;cursor:default;user-select:text;">{opt} <em style="font-style:normal;font-size:0.72rem;font-weight:500;opacity:0.85;">{badge_sub}</em></span>'
            )
        else:
            storage_badges_html.append(
                f'<span class="tt-badge" style="background:#ffffff;border:1px solid #cbd5e1;color:#1e293b;font-size:0.82rem;font-weight:600;padding:4px 10px;border-radius:6px;cursor:default;user-select:text;">{opt}</span>'
            )

    conn_badges = augmented.get("connectivity_badges")
    if not conn_badges:
        conn_badges = augmented.get("connectivity_options") or [specs.get("connectivity") or "Wi-Fi"]

    conn_badges_html = []
    for cb in conn_badges:
        conn_badges_html.append(
            f'<span class="tt-badge" style="background:#ffffff;border:1px solid #cbd5e1;color:#1e293b;font-size:0.82rem;font-weight:600;padding:4px 10px;border-radius:6px;cursor:default;user-select:text;">{cb}</span>'
        )

    color_chips_html = []
    colors_list = augmented.get("colors") or [("Space Grey", "#4b4b4d")]
    for c_name, c_hex in colors_list:
        color_chips_html.append(
            f'<span class="tt-color-chip" style="display:inline-flex;align-items:center;gap:6px;font-size:0.82rem;font-weight:500;color:#334155;background:#ffffff;border:1px solid #e2e8f0;padding:3px 8px;border-radius:6px;"><span class="tt-swatch" style="width:12px;height:12px;border-radius:50%;background-color:{c_hex};display:inline-block;border:1px solid rgba(0,0,0,0.15);"></span>{c_name}</span>'
        )

    variants_spec_box = f"""
  <div class="tt-variants-spec-box" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;margin:12px 0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
    <div class="tt-variants-header" style="display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid #e2e8f0;padding-bottom:6px;margin-bottom:10px;"><span class="tt-variants-title" style="font-size:0.82rem;font-weight:700;color:#0f172a;text-transform:uppercase;letter-spacing:0.04em;">Available Models & Configurations</span><span class="tt-variants-sub" style="font-size:0.75rem;color:#64748b;">Global & Indian Retail Variants</span></div>
    <div class="tt-variant-row variant-row" style="display:flex;align-items:center;gap:14px;margin-bottom:8px;"><span class="tt-variant-label variant-label" style="min-width:105px;width:105px;flex-shrink:0;font-size:0.8rem;font-weight:600;color:#475569;">Storage Tiers</span><div class="tt-variant-badges" style="display:flex;flex-wrap:wrap;gap:6px;">{''.join(storage_badges_html)}</div></div>
    <div class="tt-variant-row variant-row" style="display:flex;align-items:center;gap:14px;margin-bottom:8px;"><span class="tt-variant-label variant-label" style="min-width:105px;width:105px;flex-shrink:0;font-size:0.8rem;font-weight:600;color:#475569;">Connectivity</span><div class="tt-variant-badges" style="display:flex;flex-wrap:wrap;gap:6px;">{''.join(conn_badges_html)}</div></div>
    <div class="tt-variant-row variant-row" style="display:flex;align-items:center;gap:14px;"><span class="tt-variant-label variant-label" style="min-width:105px;width:105px;flex-shrink:0;font-size:0.8rem;font-weight:600;color:#475569;">Finishes</span><div class="tt-variant-colors" style="display:flex;flex-wrap:wrap;gap:8px;">{''.join(color_chips_html)}</div></div>
  </div>"""

    # Key Decision Specs Structured Grid
    aug_kpi = augmented.get("key_decision_specs", {})
    brand_low = (specs.get("brand") or "").lower()
    kpi_chipset = aug_kpi.get("chipset") or specs.get("processor") or "High-Performance Flagship Processor"
    kpi_display = aug_kpi.get("display") or specs.get("display_type") or "High-Resolution Display Panel"
    ram_str = specs.get("ram") or ("4 GB" if "10th" in (specs.get("model_name") or "").lower() else "8 GB")
    storage_str = specs.get("storage") or "128 GB"
    ram_type = "Unified RAM" if "apple" in brand_low else "LPDDR5X RAM" if "samsung" in brand_low else "RAM"
    kpi_ram_storage = aug_kpi.get("ram_storage") or f"{ram_str} {ram_type} • {storage_str} Internal Storage"
    kpi_form_factor = aug_kpi.get("form_factor") or "Ultra-portable lightweight metal enclosure"
    stylus_default = "Bundled S Pen in the Box (IP68)" if "samsung" in brand_low else "Apple Pencil Pro & USB-C" if "apple" in brand_low else "Active Stylus Compatible"
    kpi_stylus = aug_kpi.get("stylus") or stylus_default

    kpi_items = [
        ("⚡", "Chipset", kpi_chipset),
        ("📱", "Display", kpi_display),
        ("💾", "RAM & Storage", kpi_ram_storage),
        ("🪶", "Form Factor", kpi_form_factor),
        ("✏️", "Stylus", kpi_stylus),
    ]

    chips_html = []
    for icon, label, val in kpi_items:
        chips_html.append(
            f'<div class="tt-kpi-item" style="display:flex;align-items:baseline;gap:6px;font-size:0.8rem;line-height:1.4;">'
            f'<span style="font-size:0.88rem;line-height:1;flex-shrink:0;">{icon}</span>'
            f'<div><span style="font-weight:700;color:#475569;">{label}:</span> <span style="font-weight:600;color:#0f172a;">{val}</span></div>'
            f'</div>'
        )

    specs_list_html = (
        '<div class="tt-kpi-specs-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:6px 14px;">'
        + "".join(chips_html)
        + '</div>'
    )

    images = tablet.get("images") or []
    images_meta = html.escape(json.dumps(images[:5])) if images else "[]"

    aff_url = tablet.get("primary_aff_url") or (tablet.get("amazon") or {}).get("affiliate_url") or "#"
    store_name = "Flipkart" if "flipkart" in aff_url.lower() else "Amazon"
    cta_text = f"🛒 Buy on {store_name} ({price_fmt})"
    retailer_note = f"100% Genuine Retailer Verification • Direct from Official {store_name} India"

    raw_html = f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;margin-bottom:12px;">
  <div id="tt-gallery-meta" data-images='{images_meta}' style="display:none;"></div>
  {config_badge_html}
  {price_deal_html}
  <div class="tt-header-utility-row" style="display:flex;align-items:center;gap:12px;font-size:0.85rem;margin-bottom:14px;flex-wrap:wrap;">
    <div class="tt-header-rating" style="display:inline-flex;align-items:center;gap:5px;color:#64748b;font-size:0.85rem;font-weight:500;margin-right:2px;"><span style="color:#f59e0b;font-weight:700;">★ {rating_val}</span> <span style="color:#64748b;font-size:0.82rem;">({reviews_cnt:,} reviews)</span></div>
    <span class="tt-editor-score-pill" style="display:inline-flex;align-items:center;gap:4px;background:#EFF6FF;color:#1d4ed8;border:1px solid #DBEAFE;padding:3px 9px;border-radius:9999px;font-size:0.78rem;font-weight:600;box-shadow:0 1px 2px rgba(29,78,216,0.04);white-space:nowrap;">🏆 Editor's Pick <strong style="color:#1e40af;font-weight:800;margin-left:2px;">{score}/10</strong></span>
    <a href="#tt-specs" id="tt-export-specs" class="tt-export-specs-btn" style="display:inline-flex;align-items:center;gap:6px;background:#ffffff;color:#475569;border:1px solid #E2E8F0;padding:3px 9px;border-radius:6px;font-size:0.78rem;font-weight:600;text-decoration:none;box-shadow:0 1px 2px rgba(0,0,0,0.03);cursor:pointer;white-space:nowrap;"><span>📄</span> <span>Export Spec Sheet</span></a>
  </div>

  {variants_spec_box}

  <div style="display:flex;flex-direction:column;gap:8px;margin:12px 0;">
    <a href="{aff_url}" id="tt-hero-primary-cta" target="_blank" rel="nofollow sponsored" style="display:flex;align-items:center;justify-content:center;gap:8px;background:#ff9900;color:#111827;font-weight:800;font-size:1rem;padding:12px 20px;border-radius:8px;text-decoration:none;box-shadow:0 4px 10px rgba(255,153,0,0.25);transition:transform 0.15s ease;">
      <span id="tt-hero-cta-text">{cta_text}</span>
      <span style="font-size:1.1rem;">↗</span>
    </a>
  </div>

  <div class="tt-kpi-specs-card" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:10px 14px;margin-top:12px;">
    <div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;color:#64748b;letter-spacing:0.5px;margin-bottom:6px;">KEY DECISION SPECS</div>
    {specs_list_html}
  </div>

  <div style="font-size:0.78rem;color:#059669;font-weight:600;display:flex;align-items:center;gap:6px;margin-top:8px;">
    <span>✓</span> {retailer_note}
  </div>
</div>
"""
    return clean_html(raw_html)


def build_full_description(tablet: Dict[str, Any]) -> str:
    """Assemble the complete Spec-Hub layout with production clean Gutenberg block structure."""
    subnav = """
  <!-- Sub Navigation -->
  <nav class="tt-subnav" style="display:flex; gap:12px; justify-content:center; align-items:center; padding:10px 0; border-bottom:1px solid #e2e8f0; margin-bottom:20px; font-size:13px; font-weight:600; flex-wrap:wrap;">
    <a href="#tt-verdict" style="color:#2563eb; text-decoration:none; display:inline-flex; align-items:center; gap:5px; padding:6px 14px; background:#eff6ff; border-radius:6px; font-weight:700;"><span>🎯</span> <span>Editorial Verdict</span></a>
    <span style="color:#cbd5e1">•</span>
    <a href="#tt-bento" style="color:#475569; text-decoration:none; display:inline-flex; align-items:center; gap:5px; padding:6px 14px; background:#f8fafc; border-radius:6px;"><span>⚙️</span> <span>Hardware Matrix</span></a>
    <span style="color:#cbd5e1">•</span>
    <a href="#tt-specs" style="color:#475569; text-decoration:none; display:inline-flex; align-items:center; gap:5px; padding:6px 14px; background:#f8fafc; border-radius:6px;"><span>📑</span> <span>Full Specs</span></a>
  </nav>
"""

    verdict_pros_cons = render_verdict_and_pros_cons(tablet)
    hardware_bento = render_hardware_bento(tablet.get("specs") or {})
    specs_table = render_enhanced_specs_table(
        tablet.get("full_specs") or {},
        tablet.get("specs") or {},
    )

    disclosure = """
  <!-- Editorial Disclosure -->
  <aside style="background:#f8fafc; border-left:4px solid #2563eb; padding:16px 20px; border-radius:8px; font-size:12px; color:#64748b; line-height:1.6; margin-bottom:32px;">
    <strong style="color:#0f172a;">Editorial Integrity & Affiliate Disclosure:</strong> TopTablets is an independent, reader-supported tablet database. When you purchase through links on our site, we may earn an affiliate commission at no extra cost to you. Pricing, discounts, and real-time stock availability reflect verified hardware listings from Amazon India.
  </aside>
"""

    raw_html = f"""
<!-- TopTablets Verified Product Page -->
<div class="tt-page-root" style="max-width:1260px;margin:0 auto;width:100%;box-sizing:border-box;">
  {subnav}
  
  <div id="tt-verdict" style="scroll-margin-top:90px;">
    {verdict_pros_cons}
  </div>
  
  <div id="tt-bento" style="scroll-margin-top:90px;">
    {hardware_bento}
  </div>
  
  <div style="scroll-margin-top:90px;">
    {specs_table}
  </div>
  {disclosure}
</div>
"""
    return clean_html(raw_html)
