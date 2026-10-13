import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

# Storage paths
DATA_DIR = BASE_DIR / "data"
RAW_HTML_DIR = DATA_DIR / "raw_html"
DB_PATH = DATA_DIR / "tablets.db"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)

# WordPress / WooCommerce configuration
WP_SITE_URL = os.getenv("WP_SITE_URL", "").rstrip("/")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY", "")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET", "")

# Fallback basic auth (Application Password)
WP_USERNAME = os.getenv("WP_USERNAME", "")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "")

# Post settings
WC_POST_STATUS = os.getenv("WC_POST_STATUS", "draft")  # 'draft' or 'publish'
WC_DEFAULT_CATEGORY = os.getenv("WC_DEFAULT_CATEGORY", "Tablets")

# Affiliate tracking tags
AMAZON_AFFILIATE_TAG = os.getenv("AMAZON_AFFILIATE_TAG", "")
FLIPKART_AFFILIATE_ID = os.getenv("FLIPKART_AFFILIATE_ID", "")
