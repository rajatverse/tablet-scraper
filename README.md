# 📱 Tablet Scraper & WordPress/WooCommerce Publisher

A high-performance scraping, parsing, and publishing pipeline for **Amazon.in** and **Flipkart** tablet products.

Extracts rich tablet data from raw page sources, stores everything in a local SQLite database, automatically matches identical models into a **single unified product**, and publishes them to **WordPress / WooCommerce** as external affiliate products with a **side-by-side price comparison card**.

---

## 🚀 Key Features

1. **Page Source Parsers**:
   - **Amazon.in**: Extracts ASIN, title, buy-box price, MRP, ratings, reviews, high-res dynamic images, tech specs, overview table, and bullets.
   - **Flipkart**: Extracts FSN, title, price, MRP, discount, rating, review counts, 832px+ high-res images, bullet points, grouped specifications, and JSON-LD schema data.
   - **Tablet Spec Normalizer**: Standardizes Brand, Model Series, Storage (e.g. `64 GB`), RAM (e.g. `4 GB`), Screen Size (e.g. `10.9 Inch`), Connectivity (`Wi-Fi`, `5G`, `LTE`), Processor, OS, and Battery.

2. **Automated Cross-Store Model Matching**:
   - Detects identical models listed on both Amazon and Flipkart (e.g., *iPad 10th Gen 64GB Wi-Fi*).
   - Combines them into a **single tablet comparison record**.
   - Identifies the **lowest price** and calculates user savings.
   - Attaches your Amazon Associates (`tag=...`) and Flipkart Affiliate (`affid=...`) parameters to buy links.

3. **WooCommerce External / Affiliate Integration**:
   - Creates/Updates WooCommerce products with `type="external"`.
   - Sets **Regular Price** (MRP) and **Sale Price** (Best available price).
   - Generates a **Live Price Comparison Card** in the description showing Amazon vs Flipkart side-by-side with direct buy buttons.
   - Populates native **WooCommerce Product Attributes** (Brand, Display, Storage, RAM, Processor, OS, Battery) for filtering.
   - Attaches product image galleries.

4. **Local SQLite Database & Raw HTML Archive**:
   - Stores raw HTML snapshots in `data/raw_html/` and SQLite.
   - If a retailer changes page layout in the future, you can fix the parser and re-parse your saved copies without needing to re-fetch!

---

## 🛠️ Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy the environment configuration template
copy .env.example .env
```

---

## ⚙️ Configuration (`.env`)

Edit your `.env` file with your WordPress details:

```ini
# Your WordPress Site URL (no trailing slash)
WP_SITE_URL=https://your-wordpress-site.com

# WooCommerce REST API Credentials
# (WP Admin -> WooCommerce -> Settings -> Advanced -> REST API -> Add Key)
WC_CONSUMER_KEY=ck_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
WC_CONSUMER_SECRET=cs_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Fallback: WordPress Application Password (Optional if WC keys are set)
# (WP Admin -> Users -> Profile -> Application Passwords)
WP_USERNAME=admin
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx

# WooCommerce Settings
WC_POST_STATUS=draft          # 'draft' or 'publish'
WC_DEFAULT_CATEGORY=Tablets   # Target category name

# Affiliate Tracking Tags
AMAZON_AFFILIATE_TAG=yourtag-21
FLIPKART_AFFILIATE_ID=your_affid
```

---

## 📖 Usage Guide

### 1. Automated URL to HTML Converter (Recommended)
Automatically download the intact HTML from any product page URL, save it to `data/raw_html/`, and parse it into your database:

```powershell
# Convert a single Amazon or Flipkart product URL
python url_to_html_converter.py "https://www.amazon.in/dp/B0DK3Z6NMQ"

# Interactive prompt (asks you to paste a URL)
python url_to_html_converter.py

# Batch convert multiple URLs from a text file (one URL per line)
python url_to_html_converter.py urls.txt
```

### 2. Test WordPress Connection
Verify your WooCommerce REST API credentials:
```powershell
python cli.py test-connection
```

### 3. Parse Existing Saved HTML Files (Offline)
If you already saved `.html` files in your browser (*Ctrl + S*):
```powershell
# Parse a single file
python cli.py parse sample_data/amazon_ipad_10th_gen.html

# Parse an entire folder
python cli.py parse data/raw_html/
```

### 3. View Stored Listings & Matched Tablets
Display formatted tables of all individual listings and combined comparison products:
```bash
python cli.py list
```

### 4. Publish to WooCommerce
Post a specific tablet or all tablets to your WordPress store:
```bash
# Post by Tablet ID (from the list table)
python cli.py post-wc --id 1

# Post all unpublished tablets
python cli.py post-wc --all
```

### 5. Standalone Single-File Parsers
Run parsers directly in the terminal to inspect raw JSON output:
```bash
# Amazon
python amazon_in_parser.py sample_data/amazon_ipad_10th_gen.html

# Flipkart
python flipkart_in_parser.py sample_data/flipkart_ipad_10th_gen.html
```

---

## 📁 Project Structure

```
Tablet Scraper/
├── config.py                 # Environment variables and path settings
├── .env.example              # Config template for WooCommerce & affiliate tags
├── requirements.txt          # Python dependencies
│
├── parsers/
│   ├── __init__.py           # Unified parser entrypoint with auto-detection
│   ├── amazon_parser.py      # Amazon.in parser module
│   ├── flipkart_parser.py    # Flipkart parser module
│   └── spec_normalizer.py    # Tablet spec normalization (RAM, Display, CPU, OS)
│
├── matcher/
│   └── matcher.py            # Combines Amazon & Flipkart listings into one product
│
├── storage/
│   └── db.py                 # SQLite database for raw HTML, listings, and tablets
│
├── fetcher/
│   └── fetcher.py            # HTML loader and optional live fetcher
│
├── wordpress/
│   ├── woocommerce_client.py # WooCommerce REST API client
│   └── product_template.py   # HTML template with comparison card & specs table
│
├── cli.py                    # Rich CLI interface
├── main.py                   # Quick-start entrypoint
├── amazon_in_parser.py       # Standalone Amazon parser CLI
├── flipkart_in_parser.py     # Standalone Flipkart parser CLI
└── sample_data/              # Sample test HTML files
```
