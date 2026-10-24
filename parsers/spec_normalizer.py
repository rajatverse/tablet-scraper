import re
from typing import Dict, Any, Optional

BRANDS = [
    "Apple", "Samsung", "Lenovo", "Xiaomi", "Redmi", "OnePlus",
    "Realme", "Honor", "Google", "Motorola", "Nokia", "Acer", "Asus", "HP"
]

STORAGE_RE = re.compile(r"(\b(?:32|64|128|256|512)\s*(?:GB|gb)\b|\b1\s*(?:TB|tb)\b)", re.IGNORECASE)
RAM_RE = re.compile(r"(\b(?:2|3|4|6|8|12|16)\s*,?\s*(?:GB|gb)\s*(?:RAM)?\b)", re.IGNORECASE)
SCREEN_RE = re.compile(r"(\b\d{1,2}(?:\.\d{1,2})?\s*(?:inch|inches|\"|cm|centimetres|centimeters)\b)", re.IGNORECASE)
CONNECTIVITY_RE = re.compile(r"(wi-?fi\s*\+\s*5g|wi-?fi\s*\+\s*4g|wi-?fi\s*\+\s*cellular|wi-?fi\s*only|cellular|wi-?fi|5g|lte)", re.IGNORECASE)

def detect_brand(text: str) -> Optional[str]:
    """Detect brand from title or brand string."""
    if not text:
        return None
    for brand in BRANDS:
        if re.search(rf"\b{re.escape(brand)}\b", text, re.IGNORECASE):
            return brand
    return None

def normalize_storage(text: str) -> Optional[str]:
    """Extract storage size in standard format (e.g., '64 GB', '128 GB', '1 TB')."""
    if not text:
        return None
    m = STORAGE_RE.search(text)
    if m:
        raw = m.group(1).upper().replace(" ", "").replace(",", "")
        if "TB" in raw:
            return raw.replace("TB", " TB")
        return raw.replace("GB", " GB")
    return None

def normalize_ram(text: str) -> Optional[str]:
    """Extract RAM size in standard format (e.g., '4 GB', '8 GB')."""
    if not text:
        return None
    m = RAM_RE.search(text)
    if m:
        val = m.group(1).upper().replace("RAM", "").replace(",", "").strip()
        val = val.replace(" ", "")
        return val.replace("GB", " GB")
    return None

def normalize_screen_size(text: str) -> Optional[str]:
    """Extract screen size (e.g., '10.9 Inch')."""
    if not text:
        return None
    # Look for e.g. 10.9 inch or 27.69 cm / 27.94 Centimetres
    m = re.search(r"(\d{1,2}(?:\.\d{1,2})?)\s*(?:inch|inches|\")", text, re.IGNORECASE)
    if m:
        return f"{m.group(1)} Inch"
    
    # Check for cm/centimetres conversion (e.g., 27.94 Centimetres -> 11.0 inch)
    m_cm = re.search(r"(\d{1,2}(?:\.\d{1,2})?)\s*(?:cm|centimetres|centimeters)\b", text, re.IGNORECASE)
    if m_cm:
        cm_val = float(m_cm.group(1))
        inches = round(cm_val / 2.54, 1)
        return f"{inches} Inch"

    # Direct size number e.g. "12.1" or "11"
    m_num = re.match(r"^(\d{1,2}(?:\.\d{1,2})?)$", str(text).strip())
    if m_num:
        val = float(m_num.group(1))
        if 7.0 <= val <= 16.0:
            return f"{val} Inch"
    return None

def normalize_connectivity(text: str) -> str:
    """Classify connectivity: Wi-Fi Only, Wi-Fi + 5G, Wi-Fi + 4G/LTE, or Wi-Fi."""
    if not text:
        return "Wi-Fi"
    low = text.lower()
    if "wi-fi + 5g" in low or "wifi + 5g" in low or "cellular 5g" in low or "5g cellular" in low:
        return "Wi-Fi + 5G"
    if "wi-fi + 4g" in low or "wifi + 4g" in low or "lte" in low or "cellular" in low or "4g" in low:
        return "Wi-Fi + LTE"
    if "wi-fi only" in low or "wifi only" in low or "with wi-fi only" in low:
        return "Wi-Fi Only"
    if "5g" in low:
        return "Wi-Fi + 5G"
    return "Wi-Fi"

def clean_generation_text(text: str) -> str:
    """Normalize '10th Generation' -> '10th Gen', remove extra punctuation."""
    if not text:
        return ""
    t = re.sub(r"\b(\d+)(?:st|nd|rd|th)?\s+generation\b", r"\1th Gen", text, flags=re.IGNORECASE)
    t = re.sub(r"\b(\d+)(?:st|nd|rd|th)\s+gen\b", r"\1th Gen", t, flags=re.IGNORECASE)
    return t


def extract_model_series(title: str, brand: Optional[str], raw_model_name: Optional[str] = None) -> str:
    """Extract clean tablet series name, prioritizing structured model name."""
    generic_models = {"tablet", "hp tablet", "android tablet", "smart tablet", "ipad", "pad"}
    if raw_model_name and raw_model_name.strip().lower() not in generic_models and len(raw_model_name.strip()) > 2 and len(raw_model_name) < 40:
        cleaned_model = clean_generation_text(raw_model_name.strip())
        cleaned_model = re.sub(r"[\(\)\[\]]", " ", cleaned_model)
        cleaned_model = re.sub(r"\s+", " ", cleaned_model).strip()
        if brand and not cleaned_model.lower().startswith(brand.lower()):
            return f"{brand} {cleaned_model}"
        return cleaned_model

    clean = title
    if brand:
        clean = re.sub(rf"^{re.escape(brand)}\s*", "", clean, flags=re.IGNORECASE)

    # Common tablet patterns in title
    ipad_m = re.search(r"ipad\s+(?:pro\s+\d{1,2}|air\s*(?:\(?[a-z0-9]+\)?)?|mini\s*(?:\d+)?|\d+th\s+gen(?:eration)?|\(\d+th\s+gen(?:eration)?\))", clean, re.IGNORECASE)
    if ipad_m:
        return f"Apple {clean_generation_text(ipad_m.group(0))}"

    galaxy_m = re.search(r"galaxy\s+tab\s+[a-z0-9\+\s]+?(?=\s*\(|\s*\d{1,2}(?:\.\d+)?\s*(?:inch|\"|cm)|,|\s*with|\s*64|\s*128|\s*256|$)", clean, re.IGNORECASE)
    if galaxy_m:
        return f"Samsung {galaxy_m.group(0).strip()}"

    pad_m = re.search(r"(?:oneplus|xiaomi|redmi|lenovo|realme|hp)\s+(?:pad|omnipad|omni\s*pad)\s+[a-z0-9\+\s]+?(?=\s*\(|\s*\d{1,2}(?:\.\d+)?\s*(?:inch|\"|cm)|,|\s*with|\s*64|\s*128|\s*256|$)", clean, re.IGNORECASE)
    if pad_m:
        return pad_m.group(0).strip()

    omni_m = re.search(r"(?:omnipad|omni\s*pad)\s+[a-z0-9\+\s]+?(?=\s*\(|\s*\d{1,2}(?:\.\d+)?\s*(?:inch|\"|cm)|,|\s*with|\s*64|\s*128|\s*256|$)", clean, re.IGNORECASE)
    if omni_m:
        return f"HP {omni_m.group(0).strip()}"

    # Remove storage, connectivity, screen size, color, accessories from title
    patterns_to_remove = [
        r"\(?\s*(?:32|64|128|256|512)\s*(?:GB|gb|ROM)\s*\)?",
        r"\(?\s*1\s*(?:TB|tb)\s*\)?",
        r"\(?\s*(?:2|3|4|6|8|12|16)\s*(?:GB|gb)\s*RAM\s*\)?",
        r"\(?\s*\d{1,2}(?:\.\d{1,2})?\s*(?:inch|inches|\"|cm)[^,)]*\)?",
        r"\(?\s*(?:with\s*)?wi-?fi(?:\s*(?:only|\+\s*cellular|\+\s*5g|\+\s*4g))?\s*\)?",
        r"\b(?:Blue|Silver|Space Grey|Space Gray|Pink|Yellow|Graphite|Mint|Lavender|Black|Gold)\b",
        r"with\s+[A-Za-z0-9\s]+chip",
        r"[:–\-\|].*$",
    ]
    for pat in patterns_to_remove:
        clean = re.sub(pat, "", clean, flags=re.IGNORECASE)

    # Clean whitespace and brackets
    clean = clean_generation_text(clean)
    clean = re.sub(r"[\(\)\[\]]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    if brand and not clean.lower().startswith(brand.lower()):
        return f"{brand} {clean}".strip()
    return clean


def normalize_tablet_specs(title: str, specs_dict: Dict[str, Any], overview_dict: Dict[str, Any] = None) -> Dict[str, Any]:
    """Synthesize structured tablet specifications from title, overview, and tech specs."""
    overview = overview_dict or {}

    brand = (
        overview.get("Brand") or
        overview.get("Manufacturer") or
        specs_dict.get("Brand") or
        specs_dict.get("Manufacturer") or
        detect_brand(title)
    )

    raw_model = (
        overview.get("Model Name") or
        specs_dict.get("Model Name") or
        specs_dict.get("Model Series") or
        None
    )

    storage = (
        normalize_storage(overview.get("Memory Storage Capacity", "")) or
        normalize_storage(specs_dict.get("Internal Storage", "")) or
        normalize_storage(specs_dict.get("Hard Drive Size", "")) or
        normalize_storage(title)
    )

    ram = (
        normalize_ram(overview.get("RAM Memory Installed Size", "")) or
        normalize_ram(specs_dict.get("RAM", "")) or
        normalize_ram(specs_dict.get("RAM Memory Installed", "")) or
        normalize_ram(specs_dict.get("RAM Size", "")) or
        normalize_ram(overview.get("RAM Size", "")) or
        normalize_ram(title)
    )

    screen = (
        normalize_screen_size(overview.get("Screen Size", "")) or
        normalize_screen_size(specs_dict.get("Display Size", "")) or
        normalize_screen_size(specs_dict.get("Size", "")) or
        normalize_screen_size(specs_dict.get("Screen Size Unit of Measure", "")) or
        normalize_screen_size(specs_dict.get("Standing screen display size", "")) or
        normalize_screen_size(title)
    )

    conn_text = " ".join([
        title,
        overview.get("Connectivity Technology", ""),
        specs_dict.get("Connectivity", ""),
        specs_dict.get("Internet Connectivity", ""),
        specs_dict.get("Network Connectivity Technology", ""),
        specs_dict.get("Cellular Technology", ""),
        specs_dict.get("Wireless Technology Type", ""),
        specs_dict.get("Style Name", "")
    ])
    connectivity = normalize_connectivity(conn_text)

    os_candidates = [
        overview.get("Operating System"),
        specs_dict.get("Operating Systems"),
        specs_dict.get("Operating System"),
        specs_dict.get("Operating System Family"),
    ]
    os_val = None
    for cand in os_candidates:
        if cand:
            s_cand = str(cand).strip()
            if s_cand.lower() not in ["ost", "other", "unknown", "n/a", "none"]:
                os_val = s_cand
                break
    if not os_val or os_val.lower() == "ost":
        if brand == "Apple":
            os_val = "iPadOS"
        elif brand in ["Samsung", "Lenovo", "Xiaomi", "OnePlus", "Realme", "Motorola", "HP"]:
            os_val = "Android"

    processor = (
        overview.get("CPU Model") or
        specs_dict.get("Processor Description") or
        specs_dict.get("Processor Type") or
        specs_dict.get("Processor Speed") or
        specs_dict.get("Processor") or
        specs_dict.get("Processor Brand") or
        None
    )
    if processor:
        proc_l = processor.lower()
        if "dimensity 9300" in proc_l:
            processor = "MediaTek Dimensity 9300+"
        elif "dimensity 7300" in proc_l:
            processor = "MediaTek Dimensity 7300-Ultra"
        elif "dimensity 6300" in proc_l:
            processor = "MediaTek Dimensity 6300"
        elif "g100" in proc_l or "mtk g100" in proc_l:
            processor = "MediaTek Helio G100"
        elif "snapdragon 8s gen 4" in proc_l:
            processor = "Snapdragon 8s Gen 4"
        elif "snapdragon 8 gen 3" in proc_l:
            processor = "Snapdragon 8 Gen 3"
        elif "sm6475" in proc_l or "snapdragon 7s" in proc_l:
            processor = "Qualcomm Snapdragon 7s Gen 2 (SM6475Q)"

    battery = (
        specs_dict.get("Battery Capacity") or
        specs_dict.get("Battery Power") or
        specs_dict.get("Battery") or
        specs_dict.get("Average Battery Life (in hours)") or
        None
    )
    if battery:
        battery_str = str(battery).strip()
        m_bat = re.search(r"(\d{3,5})", battery_str)
        if m_bat and int(m_bat.group(1)) >= 1000:
            battery = f"{int(m_bat.group(1)):,} mAh"
        elif battery_str.isdigit():
            battery = f"{int(battery_str):,} mAh"
        elif not battery_str.lower().endswith("mah") and not battery_str.lower().endswith("hours") and re.match(r"^\d+$", battery_str):
            battery = f"{int(battery_str):,} mAh"
    if not battery:
        watt_hours = specs_dict.get("Lithium Battery Energy Content")
        if watt_hours:
            m_wh = re.search(r"(\d+(?:\.\d+)?)\s*(?:watt\s*hours|wh)", str(watt_hours), re.IGNORECASE)
            if m_wh:
                wh_val = float(m_wh.group(1))
                mah_approx = int((wh_val / 3.8) * 1000)
                battery = f"{int(wh_val)} Wh (~{mah_approx:,} mAh)"
        if not battery and "hours battery" in title.lower():
            m_hb = re.search(r"(?:upto|up\s*to)?\s*(\d{1,2})\s*hours\s*battery", title, re.IGNORECASE)
            if m_hb:
                battery = f"Up to {m_hb.group(1)} Hours"

    color = (
        overview.get("Colour") or
        overview.get("Color") or
        specs_dict.get("Colour") or
        specs_dict.get("Color") or
        None
    )
    if color:
        color = re.sub(r"\s+\d+$", "", str(color)).strip()
    # Check title for specific finishes
    color_m = re.search(r"\b(Platinum Silver|Moonstone Gray|Space Grey|Space Gray|Starlight|Midnight|Silver|Graphite|Rose Gold|Mint|Lavender|Bronze Green|Aero Blue|Shadow Black)\b", title, re.IGNORECASE)
    if color_m and (not color or color.lower() in ["silver", "gray", "grey", "black", "green", "blue"]):
        color = color_m.group(1).title()

    # Determine base display type from specs, overview, and title
    raw_display_type = (
        overview.get("Display Type") or
        specs_dict.get("Display Type") or
        ""
    )
    combined_display_text = f"{title} {raw_display_type} {raw_model or ''}".lower()
    if "dynamic amoled 2x" in combined_display_text:
        display_type = "Dynamic AMOLED 2X (120Hz)"
    elif "super amoled" in combined_display_text:
        display_type = "Super AMOLED (120Hz)"
    elif "amoled" in combined_display_text:
        display_type = "AMOLED Display"
    elif "oled" in combined_display_text:
        display_type = "OLED Display"
    elif "liquid retina" in combined_display_text:
        display_type = "Liquid Retina IPS LCD"
    elif raw_display_type:
        display_type = raw_display_type.title()
    else:
        display_type = "IPS LCD Panel"

    # Inject technically accurate hardware specs for known product lines
    if brand == "Apple":
        low_title = (title + " " + (raw_model or "")).lower()
        if "a17 pro" in low_title or "mini" in low_title:
            ram = "8 GB"  # Apple Intelligence requirement
            os_val = "iPadOS 18"
            processor = "Apple A17 Pro (6-core)"
            screen = screen or "8.3 Inch"
            display_type = "8.3\" Liquid Retina IPS LCD (2266 x 1488, 500 nits, True Tone, P3)"
            battery = battery or "Up to 10 Hours (19.3 Wh)"
        elif "m4" in low_title:
            ram = "8 GB / 16 GB"
            os_val = "iPadOS 18"
            processor = "Apple M4"
            display_type = "Ultra Retina XDR Tandem OLED (120Hz ProMotion)"
            battery = battery or "Up to 10 Hours"
        elif "m2" in low_title or "air" in low_title:
            ram = "8 GB"
            os_val = "iPadOS 18"
            processor = "Apple M2"
            display_type = "Liquid Retina IPS LCD (500 nits, P3 Wide Color)"
            battery = battery or "Up to 10 Hours"
        elif "10th" in low_title or "a14" in low_title:
            ram = "4 GB"
            os_val = "iPadOS 18"
            processor = "Apple A14 Bionic"
            screen = screen or "10.9 Inch"
            display_type = "10.9\" Liquid Retina IPS LCD (2360 x 1640, 500 nits, True Tone)"
            battery = battery or "Up to 10 Hours"
    elif brand == "Samsung":
        low_title = (title + " " + (raw_model or "")).lower()
        if "s10+" in low_title or "s10 plus" in low_title:
            ram = ram or "12 GB"
            screen = screen or "12.4 Inch"
            display_type = "12.4\" Dynamic AMOLED 2X (2800 × 1752, 120Hz, Anti-Reflective)"
            processor = "MediaTek Dimensity 9300+"
            os_val = "Android 14 (One UI 6.1.1)"
            battery = "10,090 mAh"
            color = color or "Platinum Silver"
        elif "s10 ultra" in low_title:
            ram = ram or "12 GB / 16 GB"
            screen = screen or "14.6 Inch"
            display_type = "14.6\" Dynamic AMOLED 2X (2960 × 1848, 120Hz, Anti-Reflective)"
            processor = "MediaTek Dimensity 9300+"
            os_val = "Android 14 (One UI 6.1.1)"
            battery = "11,200 mAh"
        elif "s9" in low_title:
            display_type = "Dynamic AMOLED 2X (120Hz)"
            os_val = os_val or "Android 14 (One UI 6)"

    model_name = extract_model_series(title, brand, raw_model)

    return {
        "brand": brand,
        "model_name": model_name,
        "screen_size": screen,
        "display_type": display_type,
        "storage": storage,
        "ram": ram,
        "connectivity": connectivity,
        "operating_system": os_val,
        "processor": processor,
        "battery": battery,
        "color": color,
    }
